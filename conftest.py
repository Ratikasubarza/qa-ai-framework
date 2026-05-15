"""
Root conftest — session-level hooks, shared fixtures, plugin activation.

Hook execution order:
  pytest_configure → pytest_sessionstart → [collection] → pytest_collection_modifyitems
  → [per-test: setup / call / teardown via conftest_debug] → pytest_sessionfinish
"""
import os
import time
import pytest
import structlog
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")
logger = structlog.get_logger(__name__)

# ── Activate plugins ───────────────────────────────────────────────────────────
pytest_plugins = ["conftest_debug"]

# ── Required env vars for API/agent tests ─────────────────────────────────────
_REQUIRED_FOR_API = ["HONO_API_KEY"]
_REQUIRED_FOR_AGENTS = ["OPENROUTER_API_KEY"]


# ── Marker registration ────────────────────────────────────────────────────────
def pytest_configure(config):
    config.addinivalue_line("markers", "smoke: happy-path end-to-end — run first")
    config.addinivalue_line("markers", "security: auth, RBAC, and access-control assertions")
    config.addinivalue_line("markers", "negative: expected rejection and error cases")
    config.addinivalue_line("markers", "boundary: edge values, limits, overflow")
    config.addinivalue_line("markers", "performance: response time SLA assertions")
    config.addinivalue_line("markers", "agent: LLM agent quality gates (evals)")
    config.addinivalue_line("markers", "mobile: Appium Android tests — requires device")
    config.addinivalue_line("markers", "web: Playwright web tests — requires browser")
    config.addinivalue_line("markers", "db: tests that write to staging DB")


# ── Session start — environment banner + guard ─────────────────────────────────
def pytest_sessionstart(session):
    from config.test_config import TestConfig

    missing_api    = [k for k in _REQUIRED_FOR_API    if not os.getenv(k)]
    missing_agents = [k for k in _REQUIRED_FOR_AGENTS if not os.getenv(k)]

    print("\n" + "=" * 60)
    print("  QA AI Framework — Test Session Starting")
    print("=" * 60)
    print(f"  ENV          : {TestConfig.ENV}")
    print(f"  API_URL      : {TestConfig.API_URL}")
    print(f"  WEB_URL      : {TestConfig.WEB_APP_URL}")
    print(f"  AUTO_CREATE_BUGS: {os.getenv('AUTO_CREATE_BUGS', 'false')}")
    if missing_api:
        print(f"  ⚠  Missing API env vars : {missing_api} — API tests may fail")
    if missing_agents:
        print(f"  ⚠  Missing agent env vars: {missing_agents} — agent evals will be skipped")
    print("=" * 60 + "\n")

    # Write Allure environment properties so the report shows context
    _write_allure_environment(TestConfig)

    session._qa_start_time = time.time()


def _write_allure_environment(config):
    allure_results = "reports/allure/results"
    os.makedirs(allure_results, exist_ok=True)
    props_path = os.path.join(allure_results, "environment.properties")
    try:
        with open(props_path, "w") as f:
            f.write(f"Environment={config.ENV}\n")
            f.write(f"API_URL={config.API_URL}\n")
            f.write(f"WEB_URL={config.WEB_APP_URL}\n")
            f.write(f"Python=3.11\n")
            f.write(f"Framework=qa-ai-framework\n")
    except Exception:
        pass  # non-fatal — allure report just won't have env tab


# ── Collection — smoke tests run first, then security, then rest ───────────────
def pytest_collection_modifyitems(config, items):
    def _priority(item) -> int:
        markers = {m.name for m in item.iter_markers()}
        if "smoke"    in markers: return 0
        if "security" in markers: return 1
        if "negative" in markers: return 2
        if "boundary" in markers: return 3
        return 4

    items.sort(key=_priority)


# ── Session finish — print summary ─────────────────────────────────────────────
def pytest_sessionfinish(session, exitstatus):
    elapsed = time.time() - getattr(session, "_qa_start_time", time.time())
    minutes, seconds = divmod(int(elapsed), 60)

    print("\n" + "=" * 60)
    print(f"  Session finished in {minutes}m {seconds}s")
    print(f"  Exit status: {exitstatus}")
    print("=" * 60 + "\n")

    logger.info(
        "session_finished",
        exit_status=int(exitstatus),
        duration_seconds=round(elapsed, 1),
    )


# ── Shared fixtures ────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def base_url() -> str:
    from config.test_config import TestConfig
    return TestConfig.WEB_APP_URL


@pytest.fixture(scope="session")
def api_url() -> str:
    from config.test_config import TestConfig
    return TestConfig.API_URL


@pytest.fixture(autouse=True)
def _skip_if_missing_agent_key(request):
    """Auto-skip agent eval tests when OPENROUTER_API_KEY is absent."""
    if request.node.get_closest_marker("agent"):
        if not os.getenv("OPENROUTER_API_KEY"):
            pytest.skip("OPENROUTER_API_KEY not set — agent eval skipped")
