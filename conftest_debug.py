"""
Debug Conftest Plugin — auto-creates Jira bugs when tests fail.
Add to conftest.py: pytest_plugins = ["conftest_debug"]

Or import selectively:
  from conftest_debug import pytest_runtest_makereport
"""
import os
import pytest
import structlog

logger = structlog.get_logger(__name__)

# Set to True to auto-create Jira bugs on failure
AUTO_CREATE_BUGS = os.getenv("AUTO_CREATE_BUGS", "false").lower() == "true"
DEBUG_PLATFORM   = os.getenv("DEBUG_PLATFORM", "web")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook into pytest test execution — capture failures."""
    outcome = yield
    report  = outcome.get_result()

    if report.when == "call" and report.failed:
        _handle_failure(item, report)


def _handle_failure(item, report):
    """Process a test failure — analyze and optionally create bug."""
    test_name = item.nodeid
    longrepr  = str(report.longrepr) if report.longrepr else ""

    logger.warning("test_failed", test=test_name)

    # Try to get screenshot from test
    screenshot = None
    if hasattr(item, "funcargs"):
        page = item.funcargs.get("page")
        if page:
            try:
                screenshot_path = f"reports/debug_logs/failure_{test_name.replace('/', '_')}.png"
                page.screenshot(path=screenshot_path)
                screenshot = screenshot_path
                logger.info("failure_screenshot", path=screenshot_path)
            except Exception:
                pass

    if AUTO_CREATE_BUGS:
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
    else:
        logger.info(
            "bug_creation_skipped",
            reason="AUTO_CREATE_BUGS=false",
            test=test_name,
        )
