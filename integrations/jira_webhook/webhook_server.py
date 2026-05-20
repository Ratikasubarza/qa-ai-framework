"""
Phase 10 — Jira Webhook Server
Listens for Jira events and triggers the QA pipeline or GitHub Actions.

Security hardening applied:
  - HMAC-SHA256 signature verification (fails closed when secret unset)
  - Replay protection: 5-minute timestamp window
  - Event deduplication: LRU-bounded in-memory set (survives per-process lifetime)
  - Per-issue concurrency guard: only one pipeline run per issue_key at a time
  - Rate limiting: 30 requests/minute per IP via slowapi

Flows:
  1. Ticket → "READY TO TEST" → trigger test pipeline
  2. New Bug ticket → generate test case via AI
  3. Sprint started → run full regression
  4. Manual trigger → run specific suite
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import subprocess
import time
from collections import OrderedDict
from datetime import datetime
from typing import Optional

import httpx
import structlog
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from pydantic import ValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from core.exceptions import WebhookValidationError
from core.schemas.jira_webhook_schema import JiraWebhookEvent

load_dotenv(dotenv_path=".env")
logger = structlog.get_logger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
GITHUB_TOKEN          = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO           = os.getenv("GITHUB_REPOSITORY", "Ratikasubarza/qa-ai-framework")
TELEGRAM_TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT         = os.getenv("TELEGRAM_QA_OPS_CHAT_ID", "")
JIRA_URL              = os.getenv("JIRA_BASE_URL", "")
JIRA_EMAIL            = os.getenv("JIRA_EMAIL", "")
JIRA_TOKEN            = os.getenv("JIRA_TOKEN", "")
JIRA_WEBHOOK_SECRET   = os.getenv("JIRA_WEBHOOK_SECRET", "")
MANUAL_TRIGGER_SECRET = os.getenv("MANUAL_TRIGGER_SECRET", "")

# ── Startup guards — fail fast on missing required config ─────────────────────
_REQUIRED_ENV = {
    "GITHUB_TOKEN":     GITHUB_TOKEN,
    "JIRA_BASE_URL":    JIRA_URL,
    "JIRA_EMAIL":       JIRA_EMAIL,
    "JIRA_TOKEN":       JIRA_TOKEN,
    "JIRA_WEBHOOK_SECRET": JIRA_WEBHOOK_SECRET,
}
_missing = [k for k, v in _REQUIRED_ENV.items() if not v]
if _missing:
    raise EnvironmentError(
        f"Webhook server missing required env vars: {', '.join(_missing)}. "
        "Set them in .env before starting the server."
    )

# Replay protection window in seconds
_REPLAY_WINDOW_SECONDS = 300

# Deduplication: max unique event IDs to remember (LRU eviction above this)
_SEEN_EVENTS_MAX = 1000

# ── FastAPI app + rate limiter ─────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
app     = FastAPI(title="QA Jira Webhook", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Concurrency: one pipeline run per issue_key at a time ─────────────────────
_pipeline_locks:     dict[str, asyncio.Lock] = {}
_locks_creation_lock = asyncio.Lock()

async def _get_issue_lock(issue_key: str) -> asyncio.Lock:
    async with _locks_creation_lock:
        if issue_key not in _pipeline_locks:
            _pipeline_locks[issue_key] = asyncio.Lock()
        return _pipeline_locks[issue_key]

# ── Deduplication: LRU-bounded in-memory event ID store ───────────────────────
_seen_event_ids: OrderedDict[str, float] = OrderedDict()

def _is_duplicate_event(event_id: str) -> bool:
    if event_id in _seen_event_ids:
        return True
    _seen_event_ids[event_id] = time.monotonic()
    if len(_seen_event_ids) > _SEEN_EVENTS_MAX:
        _seen_event_ids.popitem(last=False)
    return False

# ── Replay protection ──────────────────────────────────────────────────────────
def _validate_timestamp(timestamp_ms: Optional[int]) -> None:
    if timestamp_ms is None:
        return  # Tolerate missing timestamp (older Jira Cloud versions)
    delta = abs(time.time() - timestamp_ms / 1000)
    if delta > _REPLAY_WINDOW_SECONDS:
        raise WebhookValidationError(
            f"Webhook timestamp outside {_REPLAY_WINDOW_SECONDS}s replay window.",
            context={"delta_seconds": round(delta)},
        )

# ── HMAC verification ──────────────────────────────────────────────────────────
def _unsigned_webhooks_allowed() -> bool:
    allow_unsigned = os.getenv("ALLOW_UNSIGNED_WEBHOOKS", "false").lower() == "true"
    env = os.getenv("TEST_ENV", os.getenv("ENV", "")).lower()
    return allow_unsigned and env in {"local", "dev", "development"}


def _verify_jira_signature(body: bytes, signature_header: str) -> bool:
    if not JIRA_WEBHOOK_SECRET:
        if _unsigned_webhooks_allowed():
            logger.warning("jira_webhook_unsigned_allowed_for_local_dev")
            return True
        logger.error("jira_webhook_secret_not_configured")
        return False
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        JIRA_WEBHOOK_SECRET.encode(), body, digestmod="sha256"
    ).hexdigest()
    received = signature_header[len("sha256="):]
    return hmac.compare_digest(expected, received)

# ── Telegram helper ────────────────────────────────────────────────────────────
async def send_telegram(msg: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "Markdown"},
        )

# ── GitHub Actions trigger ─────────────────────────────────────────────────────
async def trigger_github_pipeline(suite: str = "all", issue_key: str = "") -> int:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/qa-pipeline.yml/dispatches",
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept":        "application/vnd.github+json",
            },
            json={"ref": "main", "inputs": {"suite": suite, "issue_key": issue_key}},
        )
    logger.info("pipeline_triggered", resp_status=resp.status_code, suite=suite, issue=issue_key)
    return resp.status_code

# ── Jira helpers ───────────────────────────────────────────────────────────────
async def update_jira_status(issue_key: str, transition_name: str) -> None:
    import base64
    auth    = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_TOKEN}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{JIRA_URL}/rest/api/3/issue/{issue_key}/transitions", headers=headers
        )
        transitions = r.json().get("transitions", [])
        tid = next(
            (t["id"] for t in transitions if t["name"].upper() == transition_name.upper()),
            None,
        )
        if tid:
            await client.post(
                f"{JIRA_URL}/rest/api/3/issue/{issue_key}/transitions",
                headers=headers,
                json={"transition": {"id": tid}},
            )
            logger.info("jira_status_updated", issue=issue_key, status=transition_name)


async def add_jira_comment(issue_key: str, comment: str) -> None:
    import base64
    auth    = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_TOKEN}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{JIRA_URL}/rest/api/3/issue/{issue_key}/comment",
            headers=headers,
            json={"body": {
                "type": "doc", "version": 1,
                "content": [{"type": "paragraph", "content": [
                    {"type": "text", "text": comment}
                ]}],
            }},
        )

# ── Pipeline flow handlers ─────────────────────────────────────────────────────
async def handle_ready_to_test(event: JiraWebhookEvent, bg: BackgroundTasks) -> None:
    issue_key = event.issue_key
    summary   = event.issue_summary
    assignee  = (
        event.issue.fields.assignee.displayName
        if event.issue and event.issue.fields.assignee
        else "Unassigned"
    )
    logger.info("ready_to_test", issue=issue_key, summary=summary[:80])

    await update_jira_status(issue_key, "QA IN PROGRESS")
    await add_jira_comment(
        issue_key,
        f"🤖 QA Automation triggered by webhook at {datetime.now().strftime('%Y-%m-%d %H:%M')}. "
        "Running test suite... Results will be posted here.",
    )
    await send_telegram(
        f"🧪 *QA Pipeline Triggered*\n\n"
        f"*Issue:* [{issue_key}]({JIRA_URL}/browse/{issue_key})\n"
        f"*Summary:* {summary[:60]}\n"
        f"*Assignee:* {assignee}\n"
        f"*Status:* READY TO TEST → QA IN PROGRESS"
    )
    status_code = await trigger_github_pipeline(suite="all", issue_key=issue_key)
    logger.info("github_triggered", status=status_code, issue=issue_key)


async def handle_new_bug(event: JiraWebhookEvent) -> None:
    issue_key = event.issue_key
    summary   = event.issue_summary
    desc_raw  = (event.issue.fields.description or "") if event.issue else ""

    logger.info("new_bug", issue=issue_key, summary=summary[:80])
    try:
        from agents.test_case_agent import test_case_agent
        from core.agent_contracts import RequirementsDoc
        req = RequirementsDoc(
            title=f"Bug: {summary}",
            content=f"Issue: {issue_key}\nSummary: {summary}\nDescription: {str(desc_raw)[:500]}",
            source="jira_bug",
            feature_area="regression",
        )
        result   = await test_case_agent.generate(req)
        tc_text  = str(result)[:2000] if result else "Test case generation failed"
        await add_jira_comment(issue_key, f"🤖 Auto-generated test case:\n\n{tc_text}")
        await send_telegram(
            f"🐛 *New Bug — Test Case Generated*\n\n"
            f"*Issue:* [{issue_key}]({JIRA_URL}/browse/{issue_key})\n"
            f"*Summary:* {summary[:60]}\n"
            f"*Action:* Test case auto-generated and added to ticket"
        )
    except Exception as exc:
        logger.error("test_case_generation_failed", issue=issue_key, error=str(exc))


async def handle_sprint_started(event: JiraWebhookEvent) -> None:
    sprint_name = (event.sprint.name or "Unknown Sprint") if event.sprint else "Unknown Sprint"
    logger.info("sprint_started", sprint=sprint_name)
    await send_telegram(
        f"🏃 *Sprint Started — Full Regression*\n\n"
        f"*Sprint:* {sprint_name}\n"
        f"*Action:* Running full regression suite..."
    )
    await trigger_github_pipeline(suite="all", issue_key=f"sprint:{sprint_name}")


# ── Pipeline lock wrapper ──────────────────────────────────────────────────────
async def _run_with_issue_lock(
    issue_key: str,
    event: JiraWebhookEvent,
    bg: BackgroundTasks,
) -> None:
    lock = await _get_issue_lock(issue_key)
    async with lock:
        logger.info("pipeline_lock_acquired", issue_key=issue_key)
        try:
            new_status = event.new_status
            if new_status == "READY TO TEST":
                await handle_ready_to_test(event, bg)
            elif event.webhookEvent == "jira:issue_created" and event.issue_type_name == "bug":
                await handle_new_bug(event)
            elif event.webhookEvent == "sprint_started":
                await handle_sprint_started(event)
        except Exception as exc:
            logger.error("pipeline_handler_failed", issue_key=issue_key, error=str(exc))
        finally:
            logger.info("pipeline_lock_released", issue_key=issue_key)

# ── Endpoints ──────────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "qa-jira-webhook"}


@app.post("/webhook/jira")
@limiter.limit("30/minute")
async def jira_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
    raw_body = await request.body()

    # 1. HMAC verification
    sig_header = request.headers.get("X-Hub-Signature", "")
    if not _verify_jira_signature(raw_body, sig_header):
        logger.warning("jira_webhook_invalid_signature", sig=sig_header[:20])
        raise HTTPException(status_code=401, detail="Invalid signature")

    # 2. JSON parse
    try:
        import json as _json
        raw_payload = _json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # 3. Schema validation
    try:
        event = JiraWebhookEvent.model_validate(raw_payload)
    except ValidationError as exc:
        logger.warning("webhook_schema_invalid", errors=exc.errors())
        raise HTTPException(status_code=422, detail="Invalid webhook payload shape")

    # 4. Replay protection
    try:
        _validate_timestamp(event.timestamp)
    except WebhookValidationError as exc:
        logger.warning("webhook_replay_rejected", **exc.context)
        raise HTTPException(status_code=409, detail="Stale or replayed webhook event")

    # 5. Deduplication
    event_id = hashlib.sha256(raw_body).hexdigest()
    if _is_duplicate_event(event_id):
        logger.info("webhook_duplicate_ignored", event_id=event_id[:16])
        return {"status": "duplicate", "event_id": event_id[:16]}

    issue_key = event.issue_key or "global"
    logger.info(
        "webhook_accepted",
        event=event.webhookEvent,
        issue_key=issue_key,
        event_id=event_id[:16],
    )

    # 6. Concurrency guard: reject if pipeline already running for this issue
    lock = await _get_issue_lock(issue_key)
    if lock.locked():
        logger.warning("webhook_pipeline_already_running", issue_key=issue_key)
        raise HTTPException(
            status_code=429,
            detail=f"Pipeline already running for {issue_key}. Retry after it completes.",
        )

    background_tasks.add_task(_run_with_issue_lock, issue_key, event, background_tasks)
    return {"status": "accepted", "issue_key": issue_key, "event_id": event_id[:16]}


@app.post("/webhook/manual")
async def manual_trigger(request: Request, background_tasks: BackgroundTasks) -> dict:
    """
    Flow 4: Manual trigger — run specific suite.
    Body: {"suite": "api|web|mobile|all", "issue_key": "HM-XXX"}
    Requires: Authorization: Bearer <MANUAL_TRIGGER_SECRET>
    """
    if not MANUAL_TRIGGER_SECRET:
        logger.error("manual_trigger_secret_not_configured")
        raise HTTPException(status_code=503, detail="Manual trigger not configured")

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer ") or not hmac.compare_digest(
        auth_header[len("Bearer "):], MANUAL_TRIGGER_SECRET
    ):
        logger.warning(
            "manual_trigger_unauthorized",
            ip=request.client.host if request.client else "unknown",
        )
        raise HTTPException(status_code=401, detail="Unauthorized")

    body      = await request.json()
    suite     = body.get("suite", "all")
    issue_key = body.get("issue_key", "")

    logger.info("manual_trigger", suite=suite, issue=issue_key)
    status_code = await trigger_github_pipeline(suite=suite, issue_key=issue_key)

    await send_telegram(
        f"🔧 *Manual QA Trigger*\n\n"
        f"*Suite:* {suite}\n"
        f"*Issue:* {issue_key or 'N/A'}\n"
        f"*Pipeline:* {'✅ Triggered' if status_code == 204 else '❌ Failed'}"
    )

    if issue_key:
        await add_jira_comment(
            issue_key,
            f"🤖 Manual QA trigger: running {suite} suite. Results will be posted when complete.",
        )

    return {"status": "triggered", "suite": suite, "pipeline_status": status_code}
