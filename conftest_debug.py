"""
Debug Conftest Plugin — auto-creates Jira bugs when tests fail.
Add to conftest.py: pytest_plugins = ["conftest_debug"]

Or import selectively:
  from conftest_debug import pytest_runtest_makereport
"""
import os
import pytest
import structlog
from core import input_sanitizer

logger = structlog.get_logger(__name__)

# Caps longrepr before it reaches the LLM — prevents token exhaustion and
# limits PII/token surface area in case an assertion message leaks auth data.
# Truncation happens AFTER sanitization so injection patterns at byte 2001+ are caught.
_LONGREPR_MAX = 2000

# Guard: hook only executes when AUTO_CREATE_BUGS=true.
# When false the hook yields immediately — zero overhead on normal runs.
_ENABLED       = os.getenv("AUTO_CREATE_BUGS", "false").lower() == "true"
DEBUG_PLATFORM = os.getenv("DEBUG_PLATFORM", "web")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook into pytest test execution — capture failures."""
    outcome = yield
    if not _ENABLED:
        return

    report = outcome.get_result()
    if report.when == "call" and report.failed:
        _handle_failure(item, report)


def _handle_failure(item, report):
    """Process a test failure — analyze and optionally create bug."""
    test_name    = item.nodeid
    raw_longrepr = str(report.longrepr) if report.longrepr else ""

    sanitized = input_sanitizer.sanitize(raw_longrepr, source="longrepr")
    longrepr  = sanitized.content[:_LONGREPR_MAX]
    if sanitized.was_sanitized:
        logger.warning(
            "longrepr_sanitized",
            test=test_name,
            threats=sanitized.threat_count,
        )

    logger.warning("test_failed", test=test_name)

    # Try to get screenshot from test
    screenshot = None
    if hasattr(item, "funcargs"):
        page = item.funcargs.get("page")
        if page:
            try:
                worker_id = getattr(item.config, "workerinput", {}).get("workerid", "master")
                screenshot_path = f"reports/debug_logs/failure_{test_name.replace('/', '_')}_{worker_id}.png"
                page.screenshot(path=screenshot_path)
                screenshot = screenshot_path
                logger.info("failure_screenshot", path=screenshot_path)
            except Exception:
                pass

    try:
        from agents.debug_agent import debug_agent
        report_obj = debug_agent.analyze_from_pytest(
            test_name=test_name,
            longrepr=longrepr,
            platform=DEBUG_PLATFORM,
            screenshot=screenshot,
        )
        logger.info(
            "auto_bug_analyzed",
            test=test_name,
            severity=report_obj.severity,
            title=report_obj.title[:50],
        )
    except Exception as e:
        logger.error("auto_bug_failed", error=str(e))
