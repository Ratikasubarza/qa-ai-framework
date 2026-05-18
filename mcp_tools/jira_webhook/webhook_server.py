"""
Phase 10 — Jira Webhook Server
Listens for Jira events and triggers GitHub Actions pipeline.

Flows:
1. Ticket → "READY TO TEST" → trigger test pipeline
2. New Bug ticket → generate test case via AI
3. Sprint started → run full regression
4. Manual trigger → run specific suite
"""
import os
import hmac
import hashlib
import subprocess
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from dotenv import load_dotenv
import httpx
import structlog

load_dotenv(dotenv_path=".env")
logger = structlog.get_logger(__name__)

app = FastAPI(title="QA Jira Webhook", version="1.0.0")

GITHUB_TOKEN        = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO         = os.getenv("GITHUB_REPOSITORY", "Ratikasubarza/qa-ai-framework")
TELEGRAM_TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT       = os.getenv("TELEGRAM_QA_OPS_CHAT_ID", "")
JIRA_URL            = os.getenv("JIRA_BASE_URL", "")
JIRA_EMAIL          = os.getenv("JIRA_EMAIL", "")
JIRA_TOKEN          = os.getenv("JIRA_TOKEN", "")
JIRA_WEBHOOK_SECRET = os.getenv("JIRA_WEBHOOK_SECRET", "")


def _verify_jira_signature(body: bytes, signature_header: str) -> bool:
    """Verify Jira webhook HMAC-SHA256 signature.

    Jira sends: X-Hub-Signature: sha256=<hex_digest>
    Returns True when secret is unset (not configured) so existing deployments
    keep working until the secret is provisioned.
    """
    if not JIRA_WEBHOOK_SECRET:
        logger.warning("jira_webhook_secret_not_configured")
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        JIRA_WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    received = signature_header[len("sha256="):]
    return hmac.compare_digest(expected, received)


async def send_telegram(msg: str):
    """Send notification to Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "Markdown"}
        )


async def trigger_github_pipeline(suite: str = "all", issue_key: str = ""):
    """Trigger GitHub Actions workflow."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/qa-pipeline.yml/dispatches",
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json"
            },
            json={
                "ref": "main"
            }
        )
    logger.info("pipeline_triggered", resp_status=resp.status_code, suite=suite, issue=issue_key)
    return resp.status_code


async def update_jira_status(issue_key: str, transition_name: str):
    """Update Jira issue status."""
    import base64
    auth = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_TOKEN}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        # Get transitions
        r = await client.get(
            f"{JIRA_URL}/rest/api/3/issue/{issue_key}/transitions",
            headers=headers
        )
        transitions = r.json().get("transitions", [])
        transition_id = next(
            (t["id"] for t in transitions if t["name"].upper() == transition_name.upper()),
            None
        )
        if transition_id:
            await client.post(
                f"{JIRA_URL}/rest/api/3/issue/{issue_key}/transitions",
                headers=headers,
                json={"transition": {"id": transition_id}}
            )
            logger.info("jira_status_updated", issue=issue_key, status=transition_name)


async def add_jira_comment(issue_key: str, comment: str):
    """Add comment to Jira issue."""
    import base64
    auth = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_TOKEN}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{JIRA_URL}/rest/api/3/issue/{issue_key}/comment",
            headers=headers,
            json={"body": {
                "type": "doc", "version": 1,
                "content": [{"type": "paragraph", "content": [
                    {"type": "text", "text": comment}
                ]}]
            }}
        )


async def handle_ready_to_test(issue: dict, bg: BackgroundTasks):
    """Flow 1: READY TO TEST → trigger pipeline."""
    issue_key = issue.get("key")
    summary   = issue.get("fields", {}).get("summary", "")
    assignee  = issue.get("fields", {}).get("assignee", {})
    assignee_name = assignee.get("displayName", "Unassigned") if assignee else "Unassigned"

    logger.info("ready_to_test", issue=issue_key, summary=summary)

    # Update status to QA IN PROGRESS
    await update_jira_status(issue_key, "QA IN PROGRESS")

    # Add comment
    await add_jira_comment(issue_key,
        f"🤖 QA Automation triggered by webhook at {datetime.now().strftime('%Y-%m-%d %H:%M')}. "
        f"Running test suite... Results will be posted here."
    )

    # Telegram notification
    await send_telegram(
        f"🧪 *QA Pipeline Triggered*\n\n"
        f"*Issue:* [{issue_key}]({JIRA_URL}/browse/{issue_key})\n"
        f"*Summary:* {summary[:60]}\n"
        f"*Assignee:* {assignee_name}\n"
        f"*Status:* READY TO TEST → QA IN PROGRESS"
    )

    # Trigger GitHub Actions
    status_code = await trigger_github_pipeline(suite="all", issue_key=issue_key)
    logger.info("github_triggered", status=status_code, issue=issue_key)


async def handle_new_bug(issue: dict):
    """Flow 2: New Bug → generate test case via AI agent."""
    issue_key = issue.get("key")
    summary   = issue.get("fields", {}).get("summary", "")
    desc_raw  = issue.get("fields", {}).get("description", "") or ""

    logger.info("new_bug", issue=issue_key, summary=summary)

    # Generate test case via AI
    try:
        from agents.test_case_agent import test_case_agent
        from core.agent_contracts import RequirementsDoc
        req = RequirementsDoc(
            title=f"Bug: {summary}",
            content=f"Issue: {issue_key}\nSummary: {summary}\nDescription: {str(desc_raw)[:500]}",
            source="jira_bug",
            feature_area="regression"
        )
        result = await test_case_agent.generate(req)

        # Add generated test case as Jira comment
        tc_text = str(result)[:2000] if result else "Test case generation failed"
        await add_jira_comment(issue_key,
            f"🤖 Auto-generated test case:\n\n{tc_text}"
        )

        await send_telegram(
            f"🐛 *New Bug — Test Case Generated*\n\n"
            f"*Issue:* [{issue_key}]({JIRA_URL}/browse/{issue_key})\n"
            f"*Summary:* {summary[:60]}\n"
            f"*Action:* Test case auto-generated and added to ticket"
        )
    except Exception as e:
        logger.error("test_case_generation_failed", error=str(e))


async def handle_sprint_started(sprint: dict):
    """Flow 3: Sprint started → full regression."""
    sprint_name = sprint.get("name", "Unknown Sprint")
    logger.info("sprint_started", sprint=sprint_name)

    await send_telegram(
        f"🏃 *Sprint Started — Full Regression*\n\n"
        f"*Sprint:* {sprint_name}\n"
        f"*Action:* Running full regression suite..."
    )
    await trigger_github_pipeline(suite="all", issue_key=f"sprint:{sprint_name}")


# ── Webhook Endpoints ─────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "qa-jira-webhook"}


@app.post("/webhook/jira")
async def jira_webhook(request: Request, background_tasks: BackgroundTasks):
    """Main Jira webhook handler."""
    raw_body = await request.body()
    sig_header = request.headers.get("X-Hub-Signature", "")
    if not _verify_jira_signature(raw_body, sig_header):
        logger.warning("jira_webhook_invalid_signature", sig=sig_header[:20])
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        import json as _json
        payload = _json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event      = payload.get("webhookEvent", "")
    issue      = payload.get("issue", {})
    changelog  = payload.get("changelog", {})
    sprint     = payload.get("sprint", {})

    logger.info("webhook_received", webhook_event=event, issue=issue.get("key"))

    # Flow 1: Ticket moved to READY TO TEST
    if event == "jira:issue_updated" and changelog:
        for item in changelog.get("items", []):
            if item.get("field") == "status":
                new_status = item.get("toString", "").upper()
                if new_status == "READY TO TEST":
                    background_tasks.add_task(handle_ready_to_test, issue, background_tasks)
                    return {"status": "triggered", "flow": "ready_to_test", "issue": issue.get("key")}

    # Flow 2: New bug created
    if event == "jira:issue_created":
        issue_type = issue.get("fields", {}).get("issuetype", {}).get("name", "").lower()
        if issue_type == "bug":
            background_tasks.add_task(handle_new_bug, issue)
            return {"status": "triggered", "flow": "new_bug", "issue": issue.get("key")}

    # Flow 3: Sprint started
    if event == "sprint_started":
        background_tasks.add_task(handle_sprint_started, sprint)
        return {"status": "triggered", "flow": "sprint_started"}

    return {"status": "ignored", "event": event}


@app.post("/webhook/manual")
async def manual_trigger(request: Request, background_tasks: BackgroundTasks):
    """
    Flow 4: Manual trigger — run specific suite.
    Body: {"suite": "api|web|mobile|all", "issue_key": "HM-XXX"}
    """
    body = await request.json()
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
        await add_jira_comment(issue_key,
            f"🤖 Manual QA trigger: running {suite} suite. "
            f"Results will be posted when complete."
        )

    return {"status": "triggered", "suite": suite, "pipeline_status": status_code}
