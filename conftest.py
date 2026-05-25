"""
Root conftest — session-level hooks, shared fixtures, plugin activation.

Hook execution order:
  pytest_configure → pytest_sessionstart → [collection] → pytest_collection_modifyitems
  → [per-test: setup / call / teardown via conftest_debug] → pytest_sessionfinish
"""
import os
import time
import hashlib
import pytest
import structlog
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")
logger = structlog.get_logger(__name__)

# ── Activate plugins ───────────────────────────────────────────────────────────
pytest_plugins = ["conftest_debug", "conftest_shared_fixtures"]
import core.pom_registry_setup  # noqa: F401 — populates the POMRegistry singleton at session start

# ── Required env vars for API/agent tests ─────────────────────────────────────
_REQUIRED_FOR_API    = ["HONO_API_KEY"]
_REQUIRED_FOR_AGENTS = ["OPENROUTER_API_KEY"]

# ── Test email domain ──────────────────────────────────────────────────────────
# Test email domain: mailinator.com
# KNOWN LIMITATION: Mailinator is a public inbox.
# Any emails sent during staging tests are publicly readable.
# Acceptable for staging. NEVER use for production test runs.
# Alternative for production testing: use a private email domain
# configured via TEST_EMAIL_DOMAIN env var.

# ── RAG staleness check paths ──────────────────────────────────────────────────
_API_SPEC_PATH = Path("api_spec.yaml")
_RAG_HASH_FILE = Path("knowledge_base/.index_hash")


# ── CLI options ───────────────────────────────────────────────────────────────
def pytest_addoption(parser):
    parser.addoption(
        "--skip-rag-check",
        action="store_true",
        default=False,
        help="Skip RAG knowledge base staleness check at session start.",
    )


# ── RAG staleness check ────────────────────────────────────────────────────────
def _check_rag_staleness(config) -> None:
    """
    Compare SHA256 of api_spec.yaml against knowledge_base/.index_hash.
    Re-indexes the knowledge base when the spec has changed since the last run.
    Always non-blocking: any failure logs a warning and lets the session continue.
    """
    if config.getoption("--skip-rag-check", default=False):
        logger.info("rag_check_skipped", reason="--skip-rag-check flag set")
        return

    if not _API_SPEC_PATH.exists():
        logger.warning("rag_check_skipped", reason="api_spec.yaml not found at project root")
        return

    try:
        current_hash = hashlib.sha256(_API_SPEC_PATH.read_bytes()).hexdigest()
        stored_hash  = _RAG_HASH_FILE.read_text().strip() if _RAG_HASH_FILE.exists() else ""

        if current_hash == stored_hash:
            logger.info("rag_index_fresh", api_spec_hash=current_hash[:12])
            return

        logger.warning(
            "rag_index_stale",
            stored_hash  = stored_hash[:12] if stored_hash else "none",
            current_hash = current_hash[:12],
            note         = "api_spec.yaml changed since last index — re-indexing",
        )

        from knowledge_base.indexer    import index_all
        from knowledge_base.rag_engine import rag_engine

        # Re-index all configured source directories
        report = index_all()

        # Index api_spec.yaml itself — not covered by indexer.py SOURCE_CONFIGS
        rag_engine.index(
            documents  = [_API_SPEC_PATH.read_text(encoding="utf-8")],
            ids        = ["api_spec_yaml"],
            metadatas  = [{"source": "api_spec.yaml", "type": "api_spec", "feature": "all"}],
            collection = "knowledge_base",
        )

        # Persist the new hash so subsequent runs skip re-indexing
        _RAG_HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
        _RAG_HASH_FILE.write_text(current_hash)

        logger.info(
            "rag_reindexed",
            api_spec_hash = current_hash[:12],
            sources       = report,
        )

    except Exception as exc:
        logger.warning(
            "rag_reindex_failed",
            error = str(exc),
            note  = "RAG context may be stale — test session continues",
        )


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

    # Check RAG knowledge base freshness against api_spec.yaml
    _check_rag_staleness(session.config)

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


# ── Per-test structured logging ───────────────────────────────────────────────
@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item, nextitem):
    markers = [m.name for m in item.iter_markers()]
    logger.info(
        "test_starting",
        test_id=item.nodeid,
        markers=markers,
        file=str(item.fspath.basename),
    )
    return None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        markers = [m.name for m in item.iter_markers()]
        if report.passed:
            logger.info(
                "test_passed",
                test_id=item.nodeid,
                duration=round(report.duration, 3),
                markers=markers,
            )
        elif report.failed:
            logger.warning(
                "test_failed",
                test_id=item.nodeid,
                duration=round(report.duration, 3),
                markers=markers,
            )


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

    terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if terminalreporter:
        passed  = len(terminalreporter.stats.get("passed",  []))
        failed  = len(terminalreporter.stats.get("failed",  []))
        skipped = len(terminalreporter.stats.get("skipped", []))
        logger.info(
            "session_complete",
            passed=passed,
            failed=failed,
            skipped=skipped,
            total=passed + failed + skipped,
            duration_seconds=round(elapsed, 1),
        )

    try:
        from core.test_data.cleanup_registry import cleanup_registry
        run_id    = os.getenv("RUN_ID", "pytest")
        worker_id = getattr(session.config, "workerinput", {}).get("workerid", "main")
        cleaned   = cleanup_registry.cleanup_all(run_id=run_id, worker_id=worker_id)
        logger.info(
            "cleanup_registry_complete",
            cleaned_count=cleaned,
            run_id=run_id,
            worker_id=worker_id,
        )
    except Exception as e:
        logger.warning("cleanup_registry_failed", error=str(e))


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


@pytest.fixture
def cleanup(request, worker_id="main"):
    """
    Opt-in cleanup registry fixture.

    Usage:
        def test_something(cleanup):
            user_id = create_user(...)
            cleanup.register("user", user_id, lambda: delete_user(user_id))
            # cleanup_all() is called automatically after the test
    """
    from core.test_data.cleanup_registry import cleanup_registry

    try:
        wid = request.config.workerinput.get("workerid", "main")
    except AttributeError:
        wid = "main"
    run_id = os.getenv("RUN_ID", "pytest")

    yield cleanup_registry

    cleanup_registry.cleanup_all(run_id=run_id, worker_id=wid)
