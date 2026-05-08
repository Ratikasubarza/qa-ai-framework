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
1. Identify: Is this a UI bug, API bug, test code issue, or environment issue?
2. Root cause: What specifically caused the failure?
3. Severity based on user impact:
   - P0: App crashes, data loss, security issue, blocks all users
   - P1: Major feature broken, affects most users
   - P2: Minor feature broken, workaround exists
   - P3: UI/cosmetic issue, edge case
4. Steps to reproduce: Clear, numbered steps
5. Expected vs Actual: Precise statements

OUTPUT FORMAT — Return ONLY valid JSON:
{{
  "root_cause": "string — specific cause of failure",
  "bug_type": "ui_bug|api_bug|test_code|environment|regression",
  "severity": "P0|P1|P2|P3",
  "title": "string — concise bug title (max 100 chars)",
  "description": "string — detailed description",
  "steps_to_reproduce": ["string"],
  "expected_behavior": "string",
  "actual_behavior": "string",
  "affected_component": "string",
  "suggested_fix": "string — optional, if obvious",
  "needs_dev_attention": true,
  "labels": ["string"]
}}
"""


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

        system = ANALYSIS_PROMPT.format(
            test_name=failure.test_name,
            error_message=clean_error.content,
            platform=failure.platform,
            location=failure.location,
            stack_trace=clean_stack.content,
            context=context[:500],
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

        report = BugReport(
            root_cause=data.get("root_cause", "Unknown"),
            bug_type=data.get("bug_type", "ui_bug"),
            severity=data.get("severity", "P2"),
            title=data.get("title", failure.test_name)[:100],
            description=data.get("description", ""),
            steps_to_reproduce=data.get("steps_to_reproduce", []),
            expected_behavior=data.get("expected_behavior", ""),
            actual_behavior=data.get("actual_behavior", ""),
            affected_component=data.get("affected_component", ""),
            suggested_fix=data.get("suggested_fix", ""),
            needs_dev_attention=data.get("needs_dev_attention", True),
            labels=data.get("labels", ["ai-detected", "qa-automation"]),
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
        if not raw:
            return {}
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error("debug_parse_failed", error=str(e))
            return {}

    def _notify_telegram(self, report: BugReport, failure: FailureContext):
        """Send bug notification to Telegram #qa-bugs channel."""
        try:
            from core.secret_manager import secret_manager
            import httpx

            token   = secret_manager.get("telegram_bot_token")
            chat_id = secret_manager.get("telegram_qa_bugs_chat_id")

            severity_emoji = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🟢"}
            emoji = severity_emoji.get(report.severity, "⚪")

            message = (
                f"{emoji} *New Bug Detected — {report.severity}*\n\n"
                f"*Test:* `{failure.test_name}`\n"
                f"*Title:* {report.title}\n"
                f"*Type:* {report.bug_type}\n"
                f"*Component:* {report.affected_component}\n"
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
