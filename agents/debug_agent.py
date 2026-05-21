"""
Debug Agent — analyzes test failures and auto-creates Jira bug tickets.
Triggered by: test failure, self-healer failure, CI/CD pipeline.

Flow:
  1. Receive failure context (test name, error, screenshot, logs)
  2. Analyze root cause via LLM
  3. Classify severity (P0/P1/P2/P3)
  4. Generate structured bug report
  5. Create Jira bug ticket with full context
  6. Notify via Telegram #qa-bugs channel
"""
import json
import structlog
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from core.llm_client import llm_client, ModelTier
from core.circuit_breaker import get_breaker
from core import input_sanitizer

logger = structlog.get_logger(__name__)

AGENT_NAME = "debug_agent"

ANALYSIS_PROMPT = """You are a Senior QA Engineer analyzing a test failure.
Your job: identify root cause, classify severity, and write a clear bug report.

FAILED TEST: {test_name}
ERROR MESSAGE: {error_message}
PLATFORM: {platform}
URL/SCREEN: {location}

STACK TRACE:
{stack_trace}

ADDITIONAL CONTEXT:
{context}

ANALYSIS INSTRUCTIONS:
1. Root cause: What specifically caused this failure?
2. Integrity rule — NON-NEGOTIABLE:
   - Do not optimize for passing tests. Optimize for truthful test results.
   - NEVER suggest removing assertions, weakening expected values, skipping tests,
     catching exceptions to continue, or changing steps to avoid a failing product path.
   - Auto-fixes are ONLY allowed when evidence strongly shows TEST_SCRIPT_BUG,
     LOCATOR_CHANGED, or FLAKY_TIMING (and confidence ≥ 0.80).
   - PRODUCT_BUG and API_CONTRACT_CHANGED must preserve the failing signal.
3. Classify using EXACTLY one of these 10 failure types:
   - PRODUCT_BUG          — the product/API behaves incorrectly; test is correct
   - TEST_SCRIPT_BUG      — the test code itself is wrong (bad assertion, wrong step)
   - TEST_DATA_ISSUE       — missing/stale/mismatched test data caused the failure
   - ENVIRONMENT_ISSUE     — infra, network, service dependency, or CI resource issue
   - LOCATOR_CHANGED       — UI/DOM element moved/renamed; locator no longer finds it
   - ASSERTION_TOO_WEAK    — assertion passed when it should not; hidden product defect
   - API_CONTRACT_CHANGED  — API response shape/status changed without notice
   - FLAKY_TIMING          — race condition, async timing, intermittent network
   - DEPENDENCY_MISSING    — missing setup: package, service, fixture, or file not present
   - UNKNOWN               — insufficient evidence; human triage required
4. recommended_action mapping:
   - PRODUCT_BUG           → create_bug_report
   - TEST_SCRIPT_BUG       → fix_test_code
   - TEST_DATA_ISSUE        → fix_test_data
   - ENVIRONMENT_ISSUE      → report_environment_issue
   - LOCATOR_CHANGED        → update_locator
   - ASSERTION_TOO_WEAK     → strengthen_assertion
   - API_CONTRACT_CHANGED   → create_bug_report
   - FLAKY_TIMING           → investigate_flaky
   - DEPENDENCY_MISSING     → fix_dependency
   - UNKNOWN                → ask_human_triage
5. Severity based on user impact:
   - P0: App crashes, data loss, security issue, blocks all users
   - P1: Major feature broken, affects most users
   - P2: Minor feature broken, workaround exists
   - P3: UI/cosmetic issue, edge case

OUTPUT FORMAT — Return ONLY valid JSON:
{{
  "root_cause": "string — specific cause of failure",
  "bug_type": "ui_bug|api_bug|test_code|environment|regression|locator|data|contract|timing|unknown",
  "failure_classification": "PRODUCT_BUG|TEST_SCRIPT_BUG|TEST_DATA_ISSUE|ENVIRONMENT_ISSUE|LOCATOR_CHANGED|ASSERTION_TOO_WEAK|API_CONTRACT_CHANGED|FLAKY_TIMING|DEPENDENCY_MISSING|UNKNOWN",
  "confidence": 0.0,
  "recommended_action": "create_bug_report|fix_test_code|fix_test_data|report_environment_issue|update_locator|strengthen_assertion|investigate_flaky|fix_dependency|ask_human_triage",
  "auto_fix_allowed": false,
  "integrity_notes": ["string — why this classification was chosen and what must not be hidden"],
  "severity": "P0|P1|P2|P3",
  "title": "string — concise bug title (max 100 chars)",
  "description": "string — detailed description",
  "steps_to_reproduce": ["string"],
  "expected_behavior": "string",
  "actual_behavior": "string",
  "affected_component": "string",
  "suggested_fix": "string — optional, only if non-obvious",
  "needs_dev_attention": true,
  "labels": ["string"]
}}
"""

# Mapping from classification to recommended action (deterministic fallback)
_CLASSIFICATION_ACTION: dict[str, str] = {
    "PRODUCT_BUG":          "create_bug_report",
    "TEST_SCRIPT_BUG":      "fix_test_code",
    "TEST_DATA_ISSUE":       "fix_test_data",
    "ENVIRONMENT_ISSUE":     "report_environment_issue",
    "LOCATOR_CHANGED":       "update_locator",
    "ASSERTION_TOO_WEAK":    "strengthen_assertion",
    "API_CONTRACT_CHANGED":  "create_bug_report",
    "FLAKY_TIMING":          "investigate_flaky",
    "DEPENDENCY_MISSING":    "fix_dependency",
    "UNKNOWN":               "ask_human_triage",
}

# Only these classifications can ever allow auto-fix (and only at high confidence)
_AUTO_FIX_ELIGIBLE: frozenset[str] = frozenset({
    "TEST_SCRIPT_BUG", "LOCATOR_CHANGED", "FLAKY_TIMING"
})


@dataclass
class FailureContext:
    test_name:     str
    error_message: str
    platform:      str = "web"
    location:      str = ""
    stack_trace:   str = ""
    screenshot:    str | None = None
    logs:          list[str] = field(default_factory=list)
    extra_context: dict = field(default_factory=dict)


@dataclass
class BugReport:
    root_cause:         str
    bug_type:           str
    severity:           str
    title:              str
    description:        str
    steps_to_reproduce: list[str]
    expected_behavior:  str
    actual_behavior:    str
    affected_component: str
    suggested_fix:      str
    needs_dev_attention: bool
    labels:             list[str]
    failure_classification: str = "unknown"
    confidence:         float = 0.0
    recommended_action: str = "ask_human_triage"
    auto_fix_allowed:   bool = False
    integrity_notes:    list[str] = field(default_factory=list)
    jira_key:           str | None = None
    created_at:         datetime = field(default_factory=datetime.now)


class DebugAgent:
    def __init__(self):
        self.breaker = get_breaker(AGENT_NAME)

    def analyze(self, failure: FailureContext) -> BugReport:
        """
        Analyze a test failure and return structured bug report.
        Does NOT create Jira ticket — call create_bug() for that.
        """
        logger.info(
            "debug_agent_start",
            test=failure.test_name,
            platform=failure.platform,
        )

        # Build context string
        context = ""
        if failure.logs:
            context += "Logs:\n" + "\n".join(failure.logs[-20:])
        if failure.extra_context:
            context += f"\nExtra: {json.dumps(failure.extra_context)}"

        clean_error = input_sanitizer.sanitize(
            failure.error_message, source="test_error"
        )
        clean_stack = input_sanitizer.sanitize(
            failure.stack_trace[:2000], source="stack_trace"
        )

        clean_test_name = input_sanitizer.sanitize(failure.test_name, source="test_name").content
        clean_location = input_sanitizer.sanitize(failure.location, source="location").content
        clean_context = input_sanitizer.sanitize(context[:500], source="test_context").content

        system = ANALYSIS_PROMPT.format(
            test_name=clean_test_name,
            error_message=clean_error.content,
            platform=failure.platform,
            location=clean_location,
            stack_trace=clean_stack.content,
            context=clean_context,
        )

        def _call():
            return llm_client.complete_text(
                system=system,
                user=f"Analyze failure: {failure.test_name}",
                tier=ModelTier.STANDARD,
                agent_name=AGENT_NAME,
                json_mode=True,
            )

        response = self.breaker.call(_call)
        data     = self._parse_response(response.content)

        # Deterministic severity override when LLM fails or returns default
        _sev = data.get("severity", "P2")
        if not data.get("severity"):
            _err = (failure.error_message or "").lower()
            _name = (failure.test_name or "").lower()
            if any(k in _err for k in ["all users", "blocks all", "crash", "data loss"]):
                _sev = "P0"
            elif any(k in _name for k in ["smoke", "login", "auth"]):
                _sev = "P1"

        failure_classification = data.get("failure_classification", "UNKNOWN").upper()
        if failure_classification not in _CLASSIFICATION_ACTION:
            failure_classification = "UNKNOWN"

        confidence = float(data.get("confidence", 0.0) or 0.0)

        # Deterministic recommended_action: prefer LLM output but fall back to taxonomy map
        recommended_action = data.get("recommended_action") or _CLASSIFICATION_ACTION.get(
            failure_classification, "ask_human_triage"
        )

        # Auto-fix: only eligible types AND only at high confidence
        auto_fix_allowed = bool(data.get("auto_fix_allowed", False))
        if failure_classification not in _AUTO_FIX_ELIGIBLE:
            auto_fix_allowed = False
        if confidence < 0.8:
            auto_fix_allowed = False

        report = BugReport(
            root_cause=data.get("root_cause", "Unknown"),
            bug_type=data.get("bug_type", "ui_bug"),
            severity=_sev,
            title=data.get("title", failure.test_name)[:100],
            description=data.get("description", ""),
            steps_to_reproduce=data.get("steps_to_reproduce", []) or [
                f"Run test: {failure.test_name}",
                f"Error: {(failure.error_message or '')[:150]}",
            ],
            expected_behavior=data.get("expected_behavior", ""),
            actual_behavior=data.get("actual_behavior", ""),
            affected_component=data.get("affected_component", ""),
            suggested_fix=data.get("suggested_fix", ""),
            needs_dev_attention=data.get("needs_dev_attention", True),
            labels=data.get("labels", ["ai-detected", "qa-automation"]),
            failure_classification=failure_classification,
            confidence=confidence,
            recommended_action=recommended_action,
            auto_fix_allowed=auto_fix_allowed,
            integrity_notes=data.get("integrity_notes", []) or [],
        )

        logger.info(
            "debug_analysis_complete",
            severity=report.severity,
            bug_type=report.bug_type,
            title=report.title[:50],
        )
        return report

    def create_bug(
        self,
        failure: FailureContext,
        parent_story: str | None = None,
    ) -> BugReport:
        """
        Full pipeline: analyze failure → create Jira bug ticket.
        Returns BugReport with jira_key populated.
        """
        report = self.analyze(failure)

        try:
            from skills.reporting.jira_connector import jira_connector

            # Build description
            steps = "\n".join(f"# {s}" for s in report.steps_to_reproduce)
            description = (
                f"h3. Root Cause\n{report.root_cause}\n\n"
                f"h3. Steps to Reproduce\n{steps}\n\n"
                f"h3. Expected Behavior\n{report.expected_behavior}\n\n"
                f"h3. Actual Behavior\n{report.actual_behavior}\n\n"
                f"h3. Affected Component\n{report.affected_component}\n\n"
            )
            if report.suggested_fix:
                description += f"h3. Suggested Fix\n{report.suggested_fix}\n\n"
            if failure.screenshot:
                description += f"h3. Screenshot\n!{failure.screenshot}!\n\n"
            description += (
                f"----\n"
                f"Detected by: Debug Agent | "
                f"Test: {failure.test_name} | "
                f"Platform: {failure.platform} | "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )

            # Priority mapping
            priority_map = {"P0": "Highest", "P1": "High", "P2": "Medium", "P3": "Low"}
            priority     = priority_map.get(report.severity, "Medium")

            fields = {
                "project":     {"key": jira_connector.project_key},
                "summary":     f"[BUG] {report.title}",
                "issuetype":   {"name": "Bug"},
                "priority":    {"name": priority},
                "labels":      report.labels + ["ai-detected"],
                "description": description,
            }

            issue = jira_connector.client.create_issue(fields=fields)
            key   = issue.get("key", "")

            if parent_story:
                jira_connector._link_issue(key, parent_story)

            report.jira_key = key
            logger.info("bug_created", key=key, severity=report.severity)

            # Telegram notification
            self._notify_telegram(report, failure)

        except Exception as e:
            logger.error("bug_create_failed", error=str(e))

        return report

    def analyze_from_pytest(
        self,
        test_name:   str,
        longrepr:    str,
        platform:    str = "web",
        screenshot:  str | None = None,
    ) -> BugReport:
        """
        Convenience method — called directly from pytest failure hooks.
        longrepr is pytest's full failure representation string.
        """
        lines = longrepr.split("\n")

        # Extract error message (last AssertionError or Exception line)
        error_msg = ""
        stack     = []
        for line in lines:
            if line.strip().startswith("E "):
                error_msg = line.strip()[2:]
            else:
                stack.append(line)

        failure = FailureContext(
            test_name=test_name,
            error_message=error_msg or longrepr[:200],
            platform=platform,
            stack_trace="\n".join(stack[:30]),
            screenshot=screenshot,
        )
        return self.analyze(failure)

    def _parse_response(self, raw: str | None) -> dict:
        import re
        if not raw:
            return {}
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            try:
                # Fix invalid escape sequences from LLM response
                fixed = re.sub(r'\\([^"\\/bfnrtu0-9])', r'\\\\\1', raw)
                return json.loads(fixed)
            except json.JSONDecodeError as e:
                logger.error("debug_parse_failed", error=str(e))
                return {}

    def _notify_telegram(self, report: BugReport, failure: FailureContext):
        """Send bug notification to Telegram #qa-bugs channel."""
        try:
            from core.secret_manager import secret_manager
            from core.source_intake.security import redact_internal_text
            import httpx

            token   = secret_manager.get("telegram_bot_token")
            chat_id = secret_manager.get("telegram_qa_bugs_chat_id")

            severity_emoji = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🟢"}
            emoji = severity_emoji.get(report.severity, "⚪")

            safe_test  = redact_internal_text(failure.test_name).text
            safe_title = redact_internal_text(report.title).text
            safe_comp  = redact_internal_text(report.affected_component).text

            message = (
                f"{emoji} *New Bug Detected — {report.severity}*\n\n"
                f"*Test:* `{safe_test}`\n"
                f"*Title:* {safe_title}\n"
                f"*Type:* {report.bug_type}\n"
                f"*Component:* {safe_comp}\n"
            )
            if report.jira_key:
                message += f"*Jira:* {report.jira_key}\n"

            httpx.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
                timeout=10,
            )
            logger.info("telegram_bug_notified", key=report.jira_key)
        except Exception as e:
            logger.warning("telegram_notify_failed", error=str(e))


debug_agent = DebugAgent()
