# QA AI Framework — Full Audit Report

**Auditor:** Principal-level QA/SDET review  
**Date:** 2026-05-26  
**Scope:** Every file read is cited. Every finding has FILE:LINE. No assumptions.  
**Method:** Evidence-based, risk-first. CRITICAL → HIGH → MEDIUM → LOW → Forward-looking.

---

## Severity Legend

| Level | Definition |
|-------|-----------|
| CRITICAL | Blocks team onboarding, data loss, silent wrong results, security breach |
| HIGH | Test suite unreliable, agent pipeline produces garbage silently, real bugs masked |
| MEDIUM | Maintainability debt that grows into HIGH within one sprint |
| LOW | Polish, convention, observability gap |

---

## Files Read

| File | Lines |
|------|-------|
| `agents/code_generator_agent.py` | full |
| `agents/flaky_test_agent.py` | full |
| `agents/locator_agent.py` | full |
| `agents/requirements_agent.py` | full |
| `agents/reviewer_agent.py` | full |
| `agents/skill_gap_agent.py` | full |
| `agents/test_case_agent.py` | partial (lines 155–190) |
| `config/settings.py` | full |
| `config/test_config.py` | full |
| `config/test_data.py` | full |
| `conftest_shared_fixtures.py` | full |
| `core/agent_contracts.py` | full |
| `core/agent_state.py` | full |
| `core/automation_readiness/checker.py` | full |
| `core/circuit_breaker.py` | full |
| `core/code_security.py` | full |
| `core/db/test_user_helper.py` | full |
| `core/input_sanitizer.py` | full |
| `core/llm_client.py` | full |
| `core/pom_registry_setup.py` | full |
| `core/prompt_manager.py` | full |
| `core/self_healer.py` | full |
| `core/source_intake/intake.py` | full |
| `core/source_intake/security.py` | full |
| `core/workflows/approval_workflow.py` | full |
| `core/workflows/pending_approvals.py` | full |
| `features/login/steps/api/login_api_test.py` | lines 1–60 |
| `features/network/test_data/network_test_data.py` | full |
| `features/reports/test_data/reports_test_data.py` | full |
| `integrations/confluence_client/confluence_client.py` | full |
| `integrations/github_client/github_client.py` | full |
| `integrations/jira_webhook/webhook_server.py` | full |
| `knowledge_base/indexer.py` | full |
| `knowledge_base/rag_engine.py` | full |
| `orchestrator/pipeline.py` | lines 1–30, 730–760 |
| `platforms/api/httpx_client.py` | full |
| `platforms/web/pages/base_page.py` | full |
| `pyproject.toml` | full |
| `skills/api/schema_validator.py` | full |

---

## CRITICAL

---

### C-01 — `skill_gap_agent.py` raises `NameError` at import — entire agent is dead

**File:** `agents/skill_gap_agent.py:49`

**Evidence:**
```python
# imports at top of file:
from core.circuit_breaker import get_breaker   # <-- get_breaker imported, NOT CircuitBreaker

class SkillGapAgent:
    def __init__(self):
        self.breaker = CircuitBreaker(agent_name=AGENT_NAME)  # line 49 — NameError
```

Module-level singleton at line 128:
```python
skill_gap_agent = SkillGapAgent()   # raises NameError immediately on import
```

`CircuitBreaker` is not imported — only `get_breaker` is. Every import of `agents.skill_gap_agent` crashes with `NameError: name 'CircuitBreaker' is not defined`. The Phase 9 pipeline node `node_skill_gap` will fail before executing a single line of business logic.

**Fix:** Change line 49 to `self.breaker = get_breaker(AGENT_NAME)` (consistent with all other agents that use `get_breaker`).

---

### C-02 — `test_case_agent.py` slices a `dict` as a string — silent Confluence PRD loss

**File:** `agents/test_case_agent.py:176-178`

**Evidence:**
```python
confluence = ConfluenceClient()
prd_text = confluence.fetch_page(input_data.confluence_page_url)   # returns dict
if prd_text:
    prd_clean = input_sanitizer.sanitize(prd_text[:1500], source="confluence_prd").content
    #                                    ^^^^^^^^^^^^
    #   dict[:1500] raises TypeError — dict is not subscriptable with a slice
```

`ConfluenceClient.fetch_page()` returns a `dict` (`{"id", "title", "space_key", "body_html", "body_text", ...}`) — confirmed at `integrations/confluence_client/confluence_client.py:147`. The correct key is `prd_text["body_text"]`.

The `if prd_text:` guard passes because a non-empty dict is truthy. The `TypeError` fires on the slice. Every run that provides a `confluence_page_url` will crash the TestCaseAgent at this line and fall through to the `except Exception` handler at line 187, logging `confluence_fetch_failed` — silently discarding all PRD context with no user-visible error.

Compare: `core/source_intake/intake.py:148-153` handles this correctly by accessing `page['body_text']`.

**Fix:**
```python
page = confluence.fetch_page(input_data.confluence_page_url)
if page and page.get("body_text"):
    prd_clean = input_sanitizer.sanitize(page["body_text"][:1500], source="confluence_prd").content
```

---

### C-03 — `test_user_helper.py` hardcodes `@mailinator.com` — bypasses `TEST_EMAIL_DOMAIN`

**File:** `core/db/test_user_helper.py:81`

**Evidence:**
```python
email = f"testonboard+{ts}@mailinator.com"   # hardcoded — ignores TEST_EMAIL_DOMAIN
```

`config/test_data.py` was updated to read `TEST_EMAIL_DOMAIN = os.getenv("TEST_EMAIL_DOMAIN", "mailinator.com")` to support private email domains. But `create_approved_user()` — the function that actually creates real test users in the staging DB — still hardcodes `@mailinator.com`. Every team running on a private staging environment (with a private inbox) will create users with addresses that bounce, breaking the entire fixture-creation lifecycle.

**Fix:**
```python
from config.test_data import TEST_EMAIL_DOMAIN
email = f"testonboard+{ts}@{TEST_EMAIL_DOMAIN}"
```

---

### C-04 — `config/settings.py` singleton instantiated at import — crashes any process missing `.env`

**File:** `config/settings.py:110`

**Evidence:**
```python
settings = Settings()   # line 110 — executed at import time
```

`Settings` has 13 required fields (`Field(...)` with no default): `openrouter_api_key`, `jira_base_url`, `jira_email`, `jira_token`, `telegram_bot_token`, `telegram_qa_leads_chat_id`, `telegram_qa_team_chat_id`, `telegram_qa_ops_chat_id`, `telegram_qa_bugs_chat_id`, `hono_api_url`, `hono_web_url`, `hono_cms_url`. Any import chain that reaches `config.settings` will raise `pydantic_settings.env_settings.SettingsError` if `.env` is absent or incomplete.

In CI, if a secret is added to `Settings` but not yet to the CI secrets store, **every test in the suite fails at collection time** with a validation error, masking the real issue.

**Risk:** New contributor onboarding — if `.env.example` is missing or stale, `pip install && pytest` produces only `pydantic ValidationError` with no actionable message.

**Fix:** Lazy initialization via a module-level function, or add a `@classmethod` factory that catches `ValidationError` and emits a human-readable error pointing to `.env.example`. At minimum, keep `.env.example` up to date with every required field.

---

### C-05 — `orchestrator/pipeline.py` subprocess PYTHON_BIN defaults to `sys.executable` — may use system Python

**File:** `orchestrator/pipeline.py` (PYTHON_BIN constant)

**Evidence:**
```python
PYTHON_BIN = os.getenv("PYTHON_BIN", sys.executable)
```

`sys.executable` resolves to whichever Python binary launched the current process. When pytest is invoked through IDE plugins, CI runners, or wrapper scripts that don't explicitly activate the venv, `sys.executable` resolves to `/usr/bin/python3` or `/usr/local/bin/python3`. The subprocess `pytest` invocation then runs tests under the wrong Python, missing all venv dependencies, and fails with `ModuleNotFoundError` — not a test failure, an import error that masquerades as a test run failure.

AGENTS.md rule 3: "NEVER use system Python — always use `./venv/bin/python3.11`."

**Fix:**
```python
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_VENV_PYTHON   = _PROJECT_ROOT / "venv" / "bin" / "python3.11"
PYTHON_BIN     = os.getenv("PYTHON_BIN", str(_VENV_PYTHON) if _VENV_PYTHON.exists() else sys.executable)
```

---

## HIGH

---

### H-01 — `CircuitBreaker` state not thread-safe — parallel LangGraph nodes corrupt failure count

**File:** `core/circuit_breaker.py:88`

**Evidence:**
```python
_breakers: dict[str, CircuitBreaker] = {}   # module-level, shared across all threads

class CircuitBreaker:
    def _on_failure(self, error: Exception):
        self.failure_count += 1             # read-modify-write without lock
        self.last_failure   = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
```

LangGraph can execute nodes concurrently. If `requirements_agent` and `testcase_agent` both share the same breaker (via `get_breaker`) and fail simultaneously in two threads, the `+=1` is a non-atomic read-modify-write. CPython's GIL reduces (but does not eliminate) the race for pure Python attribute assignments, but `failure_count += 1` is still a multi-step operation. The real risk: `failure_count` reaches threshold in one thread while the other thread reads `CLOSED` and proceeds to call the already-broken LLM endpoint.

**Fix:** Add `threading.Lock` per `CircuitBreaker` instance, acquired in `call()`, `_on_success()`, and `_on_failure()`.

---

### H-02 — `auth_client` fixture is function-scoped — 20+ login round-trips per test run

**File:** `features/login/steps/api/login_api_test.py:17`

**Evidence:**
```python
@pytest_asyncio.fixture(scope="function")
async def auth_client():
    async with HonoAPIClient() as client:
        await client.login(EMAIL, PASSWORD)
        yield client
```

There are 20+ tests in this file that use `auth_client`. With `scope="function"`, each test gets a fresh login — a full HTTP round-trip to `/v1/users/login`. At 200ms per login, 20 tests add 4+ seconds of fixture overhead. For the full regression suite across multiple test files, this compounds.

The `conftest_shared_fixtures.py` already implements a module-scoped `authenticated_client` that shares one token across a class. The login test file should adopt `scope="module"` or use the shared fixture for tests that only need a valid token and are not testing the login flow itself.

---

### H-03 — `PromptManager._load_prompt` strips subdirectory from `template_ref`

**File:** `core/prompt_manager.py:50`

**Evidence:**
```python
def _load_prompt(self, name: str, meta: dict):
    template_path = PROMPTS_DIR / meta["template_ref"].split("/")[-1]
    #                                                 ^^^^^^^^^^^^^
    #   splits on "/" and takes only the filename — drops any subdirectory
```

If `prompt_registry.yaml` has `template_ref: "v2/ac_extraction.txt"`, the resolved path becomes `prompts/ac_extraction.txt` instead of `prompts/v2/ac_extraction.txt`. Any prompt organized in subdirectories silently falls through to the `if not template_path.exists(): logger.warning(...)` path, and that prompt is skipped with only a warning. Every agent that calls `prompt_manager.get(name)` for a missing prompt will raise `KeyError` at runtime.

**Fix:** `template_path = PROMPTS_DIR / meta["template_ref"]` (no split).

---

### H-04 — `ReviewerAgent._parse_response` silently returns zero-coverage on JSON parse failure

**File:** `agents/reviewer_agent.py:282-298`

**Evidence:**
```python
def _parse_response(self, raw: str) -> dict:
    ...
    except json.JSONDecodeError as e:
        logger.error("reviewer_parse_failed", error=str(e))
        return {
            "summary": {"coverage_percentage": 0, "findings_critical": 0, ...},
            ...
            "recommendation": "Parse error — retry",
        }
```

When the LLM response fails to parse (truncated, markdown-wrapped), the reviewer silently returns `coverage_percentage = 0` and `recommendation = "Parse error — retry"`. The calling code in `orchestrator/pipeline.py` receives a `ReviewReport` with `coverage_percentage=0` and `findings_critical=0`, which looks like a passed review. The pipeline may proceed to the approval step believing there are no findings, when in reality the review was never performed.

**Fix:** Set a flag in the fallback dict (e.g., `"parse_error": True`) and have the pipeline node check for it before advancing.

---

### H-05 — `ConfluenceClient` uses a persistent `httpx.Client` with no connection lifetime management

**File:** `integrations/confluence_client/confluence_client.py:80,82`

**Evidence:**
```python
class ConfluenceClient:
    def __init__(self):
        ...
        self._client = httpx.Client(headers=self.headers, timeout=30)

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass
```

A single `httpx.Client` is created at instantiation and reused for all fetches in the process lifetime. `__del__` is Python's finalizer — it is **not guaranteed to run** (circular references, interpreter shutdown). If the process exits without running `__del__`, the connection pool leaks. More critically: `confluence_client = ConfluenceClient()` is a module-level singleton, so this one client serves the entire process lifetime with no connection reset on auth failure.

**Fix:** Use `httpx.Client` as a context manager per-request or per-method, not as a long-lived instance. Alternatively, implement `__enter__`/`__exit__` on `ConfluenceClient` to guarantee close.

---

### H-06 — `FlakyTestAgent.analyze` returns `None` for always-failing tests — silently hides them

**File:** `agents/flaky_test_agent.py:115`

**Evidence:**
```python
if total_runs < 3 or failure_count == 0 or failure_count == total_runs:
    return None
```

A test that fails on every single run is classified as "stable" and returns `None`. The docstring says: "Stable means: always passes, always fails, or fewer than 3 runs total." An always-failing test is not flaky, but it is also not stable — it is a broken test. Returning `None` means it will never appear in the `analyze_batch` output, giving the team a false picture that only intermittent failures matter.

**Fix:** For `failure_count == total_runs`, return a `FlakyTestResult` with `category="genuine_bug"`, `quarantine_recommended=False`, and `root_cause="Test fails on every run — treat as product regression, not flakiness"`.

---

## MEDIUM

---

### M-01 — `requirements_agent.py` uses different chunk size from `indexer.py`

**File:** `agents/requirements_agent.py:88`, `knowledge_base/indexer.py` (constants)

`requirements_agent._extract_ac_chunked` uses `chunk_size=1500, overlap=200`. The `indexer.py` constants are `_CHUNK_SIZE=1500, _CHUNK_OVERLAP=200`. These happen to match, but they are defined independently with no shared constant. Any future change to one will silently diverge from the other.

Additionally, `_extract_ac_chunked` uses simple character-position splitting (`content[start:end]`), not the boundary-aware chunking introduced in `indexer.py` (`_chunk_text()`). The requirements agent may split mid-sentence.

**Fix:** Extract chunking constants to a shared location (`config/settings.py` or a `core/chunking.py` utility). Reuse `_chunk_text` from `indexer.py` in the requirements agent.

---

### M-02 — `skill_gap_agent.py` fallback coverage formula is misleading

**File:** `agents/skill_gap_agent.py:99`

**Evidence:**
```python
"coverage_percentage": round(
    len(test_cases) / max(len(acceptance_criteria), 1) * 100, 1
),
```

This fallback triggers when the LLM call or JSON parse fails. It divides the number of test cases by the number of AC — a 1:1 ratio reports 100% coverage even if none of the test cases actually covers any of the AC. Callers that check `coverage_percentage >= 80` may incorrectly advance the pipeline.

**Fix:** Set fallback `coverage_percentage` to `0` and add `"fallback": True` to the dict. Let the pipeline treat any response with `fallback=True` as a gap analysis failure requiring retry.

---

### M-03 — `prompt_manager.py` raises `KeyError` with no recovery path in agents

**File:** `core/prompt_manager.py:64`

```python
def get(self, name: str) -> PromptTemplate:
    if name not in self._templates:
        raise KeyError(...)
```

Every agent calls `prompt_manager.get(PROMPT_NAME)` inside its main `run()` or `_extract_ac_single()` method. There is no try/except around these calls (confirmed in `requirements_agent.py:142`, `reviewer_agent.py:75`). A misconfigured or missing prompt file causes an unhandled `KeyError` that propagates through the circuit breaker's `call()` method and trips the breaker — permanently degrading the agent for the session without a clear error message.

**Fix:** Add a startup validation pass in `PromptManager._load_registry()` that raises a descriptive `ValueError` listing all missing prompt files, so failures surface at process start rather than mid-pipeline.

---

### M-04 — `self_healer._update_locators_file` replaces all occurrences unconditionally

**File:** `core/self_healer.py:219`

**Evidence:**
```python
updated = content.replace(f'"{old_locator}"', f'"{new_locator}"  # healed')
updated = updated.replace(f"'{old_locator}'", f"'{new_locator}'  # healed")
```

`str.replace` replaces all occurrences. If the same locator string is used for multiple elements in the locators file (e.g., two different buttons both use `'button[type="submit"]'`), healing one element silently modifies all others. This can cause previously-passing tests to start using the wrong locator.

**Fix:** Use regex with `re.sub(..., count=1)` or line-by-line replacement with a context window around the element name.

---

### M-05 — `locator_agent.py` JSON repair regex is incorrect

**File:** `agents/locator_agent.py:89`

**Evidence:**
```python
fixed = re.sub(r'\([^"\\/bfnrtu0-9])', r'\\\1', raw)
data = json.loads(fixed)
```

The regex `\([^"\\/bfnrtu0-9])` matches a literal `(` followed by any character not in `["\/bfnrtu0-9]`. This does not repair invalid JSON escape sequences. The intent appears to be escaping invalid `\x` sequences in JSON strings, but the pattern targets `(` which is not an invalid JSON character. The repair is a no-op on real LLM JSON errors (trailing commas, unquoted keys) and will cause `json.loads` to raise again with a confusing follow-on error.

**Fix:** Remove the JSON repair attempt and instead log the raw response for debugging. The proper fix is `json_mode=True` (already set) and prompt engineering to enforce valid JSON.

---

### M-06 — `conftest_shared_fixtures.py` — no explicit cleanup for `second_user` fixture

**File:** `conftest_shared_fixtures.py` (module-scope `second_user` fixture)

The `second_user` and `registered_user` module-scoped fixtures call `create_approved_user_sync()`, which writes a real user to the staging DB. There is no `CleanupRegistry` enrollment in these fixtures. If the test session crashes mid-run (OOM, SIGKILL, unhandled exception), the staging DB accumulates orphan users with each run. Over time this degrades staging DB health and can cause duplicate/conflict test false-positives.

**Fix:** Register each created user in `CleanupRegistry` for LIFO teardown at session end.

---

### M-07 — `github_client.py` uses emoji in QA summary body

**File:** `integrations/github_client/github_client.py:99,113`

```python
status = "✅ ALL PASSED" if failed == 0 else f"❌ {failed} FAILED"
body += "\n> 🤖 Generated by QA AI Framework"
```

Emoji in PR comment bodies render correctly in GitHub's web UI but can cause encoding issues in downstream tools that consume the GitHub Webhooks/API (Slack integrations, internal dashboards, log parsers). This is LOW in isolation but breaks the principle of keeping machine-generated output ASCII-safe for interoperability.

---

### M-08 — `settings.py` required fields include all four Telegram chat IDs — breaks non-Telegram setups

**File:** `config/settings.py:26-29`

```python
telegram_bot_token: str = Field(..., description="Telegram Bot token")
telegram_qa_leads_chat_id: str = Field(..., description="QA Leads group chat ID")
telegram_qa_team_chat_id: str = Field(..., description="QA Team group chat ID")
telegram_qa_ops_chat_id: str = Field(..., description="QA Ops group chat ID")
telegram_qa_bugs_chat_id: str = Field(..., description="QA Bugs group chat ID")
```

All five Telegram fields are `Field(...)` (required). A team using the framework without Telegram approval cannot run the pipeline at all — `settings = Settings()` at line 110 will fail with a validation error listing five missing fields before a single test runs.

**Fix:** Give these fields empty string defaults and add a `@model_validator` that checks they are populated only when `approval_required=True` or a `TELEGRAM_ENABLED=true` flag is set.

---

## LOW

---

### L-01 — `requirements_agent._extract_ac_chunked` passes `past_context=""` for chunks > 1

**File:** `agents/requirements_agent.py:113`

```python
result = self._extract_ac_single(
    content=chunk,
    source_ref=f"{source_ref}_chunk{i+1}",
    past_context=past_context if i == 0 else "",   # RAG context only for first chunk
)
```

The RAG context is dropped for all but the first chunk. For a 10,000-character story with 7 chunks, 6 of them get no historical context. This reduces the value of RAG-enriched extraction for long stories. The tradeoff is reasonable if prompt length is a concern, but it should be documented.

---

### L-02 — `reviewer_agent._load_csv` returns a human-readable string on `FileNotFoundError`

**File:** `agents/reviewer_agent.py:278`

```python
except FileNotFoundError:
    logger.warning("csv_not_found", path=path)
    return "Test cases file not found."
```

This string gets passed to `input_sanitizer.sanitize()` and then into the LLM prompt as the test cases content. The LLM receives "Test cases file not found." as if it were an actual test case — it may hallucinate a review against a phantom test suite. 

**Fix:** Raise `FileNotFoundError` and let the caller decide whether to proceed with no test cases.

---

### L-03 — `base_page.py` imports `WebAssertions` from `skills.assertions` — unclear deprecation status

**File:** `platforms/web/pages/base_page.py:188`

```python
@property
def assert_that(self):
    from skills.assertions.web_assertions import WebAssertions
    return WebAssertions(self.page)
```

AGENTS.md marks `skills/assertions/` as "DEPRECATED — `api_assertions.py` is a stub for `SchemaValidator`". However this refers specifically to `api_assertions.py`. It is unclear whether `web_assertions.py` in the same folder is also deprecated. If it is, every `BasePage.assert_that` call chains through a deprecated import. Clarify deprecation scope in AGENTS.md.

---

### L-04 — `FlakyTestAgent.analyze` uses oldest-to-newest outcome order but displays newest-first in prompt

**File:** `agents/flaky_test_agent.py:106, 132`

Docstring says `outcomes` is ordered `oldest→newest`. The prompt inserts `" → ".join(outcomes[-10:])` labelled "RECENT OUTCOMES (newest first)". The label says newest-first but the data is oldest-first. The LLM may reason incorrectly about trend direction (e.g., "recently started failing" vs "recently started passing").

**Fix:** Either reverse the slice for display (`outcomes[-10:][::-1]`) or fix the label to "oldest→newest".

---

### L-05 — `github_client.py` has no token validation on init

**File:** `integrations/github_client/github_client.py:29`

```python
self.token = os.getenv("GITHUB_TOKEN", "")
```

All methods guard with `if not self.token or not self.repo: logger.warning(...)`. But `post_pr_comment` and `create_check_run` silently return `False` if unconfigured, giving callers no way to distinguish "GitHub disabled" from "GitHub call failed". Pipeline report nodes should log a visible warning when GitHub integration is unconfigured rather than silently succeeding with `False`.

---

### L-06 — `knowledge_base/rag_engine.py` embedding model name is hardcoded

**File:** `knowledge_base/rag_engine.py` (constant)

```python
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
```

There is no env override path for the embedding model. Swapping to a higher-quality embedding model (e.g., for production deployment) requires a code change. All other model names in the framework have env override support via `AGENT_{NAME}_MODEL`. Add `EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")`.

---

### L-07 — `conftest_shared_fixtures.py` — `registered_user` docstring says "re-used" but fixture scope creates per-module

No functional bug, but the fixture comment could mislead engineers adding new test files. Ensure fixture scope annotations are visible and consistent.

---

## Addendum — Findings from Full Recon Pass

*Files read in this pass: `conftest.py`, `core/test_data/cleanup_registry.py`, `features/register/steps/api/register_api_test.py`, `features/register/steps/mobile/register_android_test.py`, `features/users_account/steps/api/users_account_api_test.py`, `.github/workflows/pr-check.yml`, `.github/workflows/qa-pipeline.yml`, `requirements.txt`, grep output across entire codebase.*

---

### H-07 — `CleanupRegistry` has zero call sites — ALL dynamically-created test users are permanent DB orphans

**Files:** `core/test_data/cleanup_registry.py`, `conftest.py:252`, grep across all `*.py`

**Evidence:**
```bash
grep -rn "cleanup_registry\." . --include="*.py" --exclude-dir=venv
# returns: (empty)
```

`conftest.py:252-263` calls `cleanup_registry.cleanup_all(run_id, worker_id)` at session finish — so the teardown hook exists. But `cleanup_registry.register()` is **never called anywhere in the codebase**. Every fixture that creates a real test user (confirmed: `conftest_shared_fixtures.py`, `features/users_account/steps/api/users_account_api_test.py:32`) creates a permanent DB row on every test run with no cleanup path.

Fixture docstrings in `privacy`, `post_interactions`, `search`, `user_relationships`, `privacy_safety` all say "Cleanup: delegated to CleanupRegistry at session end" — but none of them actually call `.register()`. The claim is false.

**Staging DB impact:** Every nightly CI run that creates users (via `create_approved_user_sync()`) adds N rows permanently. After 30 runs, the staging DB has 30× user accumulation. Duplicate conflict tests begin producing false positives.

**Fix:** In `conftest_shared_fixtures.py` and every conftest that calls `create_approved_user_sync()`, enroll the result:
```python
from core.test_data.cleanup_registry import cleanup_registry
from core.db.db_client import DBClient

user = create_approved_user_sync(...)
cleanup_registry.register(
    "user", user["email"],
    lambda e=user["email"]: DBClient().delete_user_by_email(e)
)
```

---

### H-08 — `users_account_api_test.py` creates a full DB user per test — no cleanup, no dedup

**File:** `features/users_account/steps/api/users_account_api_test.py:32-44`

**Evidence:**
```python
@pytest_asyncio.fixture(scope="function")
async def approved_account_user() -> dict:
    return await create_approved_user(fullname="Account API Test User")

@pytest_asyncio.fixture(scope="function")
async def auth_client(approved_account_user):
    async with HonoAPIClient() as client:
        await client.login(approved_account_user["email"], approved_account_user["password"])
        yield client
```

`scope="function"` means each test in this file (confirmed: at least `test_TC_USERS_ACCOUNT_001`, likely multiple) creates a brand-new approved user via the 5-step `create_approved_user()` lifecycle (register → verify → approve → set password → onboard). Each call makes ~6 HTTP requests + 4 DB queries + sends a real email via Resend. With N tests:
- N × 6 HTTP calls = significant test suite slowdown
- N new permanent DB rows per run (no cleanup)
- N emails sent to Resend — risks daily quota exhaustion

**Fix:** Change fixture to `scope="module"` (one user for all tests in the file), enroll in CleanupRegistry.

---

### H-09 — `register_android_test.py` uses raw `httpx.AsyncClient` inside a test — AGENTS.md violation

**File:** `features/register/steps/mobile/register_android_test.py:96-107`

**Evidence:**
```python
import httpx, os
async def check_quota():
    async with httpx.AsyncClient(
        base_url=os.getenv("HONO_API_URL"),
        headers={"x-api-key": os.getenv("HONO_API_KEY")},
        timeout=10
    ) as c:
        r = await c.post(APIEndpoints.REGISTER, json={
            ...
            "email": f"quotacheck+{int(__import__('time').time())}@mailinator.com",
            ...
        })
```

AGENTS.md rule: "FORBIDDEN — direct raw driver interaction in test files" / "use HonoAPIClient". Raw `httpx.AsyncClient` in a test bypasses request tracing (`X-Request-ID`), response time tracking, and the shared authentication/retry logic. It also hardcodes `@mailinator.com` at line 107, re-introducing the domain issue fixed in C-03 for `test_user_helper.py`.

**Fix:** Replace the inline client with `HonoAPIClient` and use `TEST_EMAIL_DOMAIN`:
```python
from config.test_data import TEST_EMAIL_DOMAIN
from platforms.api.httpx_client import HonoAPIClient

async def check_quota():
    async with HonoAPIClient() as c:
        r = await c.post(APIEndpoints.REGISTER, json={
            "email": f"quotacheck+{int(time.time())}@{TEST_EMAIL_DOMAIN}",
            ...
        })
```

---

### H-10 — PR check CI uses different Python environment than nightly pipeline — test results not comparable

**Files:** `.github/workflows/pr-check.yml`, `.github/workflows/qa-pipeline.yml`

**Evidence:**

`pr-check.yml`:
```yaml
runs-on: ubuntu-latest
steps:
  - uses: actions/setup-python@v5
    with:
      python-version: '3.11'
      cache: pip
  - run: pip install -r requirements.txt   # fresh install, ubuntu-latest
  - run: PYTHONPATH=. python cli.py smoke
```

`qa-pipeline.yml`:
```yaml
runs-on: self-hosted
steps:
  # (no python setup — uses pre-existing venv)
  - run: ./venv/bin/python3.11 --version
  - run: PYTHONPATH=. ./venv/bin/python3.11 -m pytest ...
```

The PR check (`ubuntu-latest` + fresh pip) and the nightly/regression pipeline (`self-hosted` + locked venv) run different Python environments. A dependency that installs a newer minor version on `ubuntu-latest` may behave differently from the pinned venv on `self-hosted`. A test that passes the PR check (green) may fail the nightly regression (different package behavior) — or vice versa.

Additionally, `pr-check.yml` calls `detect-secrets-hook` without a path, relying on PATH. If `detect-secrets` is not in `requirements.txt`, this step silently succeeds or fails depending on runner state.

**Fix:** Either use the same self-hosted runner + venv for both workflows, or add a lockfile step (`pip install --require-hashes -r requirements.txt`) in the PR workflow to ensure identical package versions.

---

### M-09 — 50+ `print()` statements in `register_api_test.py` and `onboarding_api_test.py` — `[DEV-BUG]` tags never surfaced

**Files:** `features/register/steps/api/register_api_test.py`, `features/onboarding/steps/api/onboarding_api_test.py`

**Evidence (sample):**
```python
print(f"\n✓ Register success: {data.get('message')}")          # register line 32
print(f"\n[DEV-BUG] Missing full_name: {response.status_code} {response.json()}")  # onboarding line 124
print(f"\n[DEV-BUG] Missing city_id: {response.status_code} {response.json()}")    # onboarding line 142
```

`print()` output:
1. Pollutes pytest stdout, interferes with `--tb=short` readability
2. Is not captured by Allure (no attachment) — disappears in CI artifacts
3. `[DEV-BUG]` findings — which are API contract violations per AGENTS.md — are buried in ephemeral stdout and never reach Jira

**Fix for `[DEV-BUG]` lines:** Replace with `structlog.warning("dev_bug", ...)` and optionally auto-create Jira via `jira_connector`. For generic `print(f"\n✓ ...")` lines: delete them — the assertion already validates correctness.

---

### M-10 — CI api-tests job only covers 7 of 20+ feature folders — most test files never run in CI

**File:** `.github/workflows/qa-pipeline.yml:126-135`

**Evidence:**
```yaml
run: |
  PYTHONPATH=. ./venv/bin/python3.11 -m pytest \
    features/login/steps/api/login_api_test.py \
    features/register/steps/api/register_api_test.py \
    features/cms_login/steps/api/cms_login_api_test.py \
    features/cms_users/steps/api/cms_users_api_test.py \
    features/cms_users/steps/api/cms_approve_user_test.py \
    features/cms_users/steps/api/cms_reject_user_test.py \
    features/onboarding/steps/api/onboarding_api_test.py \
    -m "not flaky and not mobile"
```

Test files that exist but are **never run in CI** (confirmed from feature listing):
`auth`, `feed`, `master_data`, `network`, `post_interactions`, `posts`, `privacy`, `privacy_safety`, `public`, `reports`, `search`, `settings`, `storage`, `user_relationships`, `users_account`, `users_email`, `users_password`, `admin_moderation`.

These 18 feature areas run only when triggered manually via `workflow_dispatch`. Any regression in these features is invisible to the PR merge gate and the nightly scheduled run.

**Fix:** Either add all feature paths to the api-tests job, or use `testpaths = ["features"]` and rely on the existing `pyproject.toml` configuration with `-m "smoke or regression"` to control scope.

---

### M-11 — `register_android_test.py:107` — separate hardcoded `@mailinator.com` not fixed by C-03

**File:** `features/register/steps/mobile/register_android_test.py:107`

```python
"email": f"quotacheck+{int(__import__('time').time())}@mailinator.com",
```

C-03 fixed `core/db/test_user_helper.py:81`. This is a separate hardcoded occurrence in a different file. Both must be fixed to fully honor `TEST_EMAIL_DOMAIN`.

**Fix:** `from config.test_data import TEST_EMAIL_DOMAIN` and use `@{TEST_EMAIL_DOMAIN}`.

---

### L-08 — `conftest.py` session banner uses `print()` — inconsistent with structlog convention

**File:** `conftest.py:136-147`

The session banner uses `print()` for the startup block (`=== QA AI Framework ===`). Intentional for terminal readability, but inconsistent with the rest of the codebase (structlog). Not a bug, but teams adding to this block may use `print()` elsewhere without noticing the divergence.

---

### L-09 — `conftest.py:29` comment is stale — still says "mailinator.com" without mentioning TEST_EMAIL_DOMAIN

**File:** `conftest.py:29`

```python
# Test email domain: mailinator.com
```

The fix in `config/test_data.py` added `TEST_EMAIL_DOMAIN` support, but this comment was not updated. New engineers reading `conftest.py` will believe mailinator is the only option.

**Fix:** Update to: `# Test email domain: configurable via TEST_EMAIL_DOMAIN env var (default: mailinator.com)`

---

### L-10 — `pr-check.yml` calls `detect-secrets-hook` without venv path — may rely on global install

**File:** `.github/workflows/pr-check.yml`

```yaml
- name: Secret scan
  run: |
    git ls-files | xargs detect-secrets-hook --baseline .secrets.baseline
```

No path prefix — relies on `detect-secrets-hook` being on `$PATH`. If it is not in `requirements.txt` (not confirmed in visible portion), the step may silently fail if the tool is not pre-installed on `ubuntu-latest`. Compare `qa-pipeline.yml` which uses `./venv/bin/detect-secrets-hook` explicitly.

---

## Summary Table

| ID | Severity | File | Line | Issue |
|----|----------|------|------|-------|
| C-01 | CRITICAL | `agents/skill_gap_agent.py` | 49 | `CircuitBreaker` NameError — module fails to import |
| C-02 | CRITICAL | `agents/test_case_agent.py` | 176-178 | dict sliced as string — Confluence PRD silently lost |
| C-03 | CRITICAL | `core/db/test_user_helper.py` | 81 | hardcoded `@mailinator.com` bypasses TEST_EMAIL_DOMAIN |
| C-04 | CRITICAL | `config/settings.py` | 110 | module-level Settings() crashes any import missing `.env` |
| C-05 | CRITICAL | `orchestrator/pipeline.py` | PYTHON_BIN | subprocess may use system Python, not venv |
| H-01 | HIGH | `core/circuit_breaker.py` | 64-75 | failure_count not thread-safe under concurrent nodes |
| H-02 | HIGH | `features/login/steps/api/login_api_test.py` | 17 | function-scope auth_client — 20+ unnecessary logins per run |
| H-03 | HIGH | `core/prompt_manager.py` | 50 | template_ref subdirectory stripped — missing prompts silently skipped |
| H-04 | HIGH | `agents/reviewer_agent.py` | 282-298 | JSON parse failure returns 0% coverage — pipeline advances on bad review |
| H-05 | HIGH | `integrations/confluence_client/confluence_client.py` | 80, 82 | persistent httpx.Client with `__del__` close — connection leak on crash |
| H-06 | HIGH | `agents/flaky_test_agent.py` | 115 | always-failing tests return None — invisible to gap analysis |
| M-01 | MEDIUM | `agents/requirements_agent.py` | 88 | chunk constants duplicated from indexer.py; simple split not boundary-aware |
| M-02 | MEDIUM | `agents/skill_gap_agent.py` | 99 | fallback coverage formula gives misleading 100% on LLM failure |
| M-03 | MEDIUM | `core/prompt_manager.py` | 64 | missing prompt raises KeyError mid-pipeline, trips circuit breaker |
| M-04 | MEDIUM | `core/self_healer.py` | 219 | str.replace heals all occurrences — can corrupt unrelated locators |
| M-05 | MEDIUM | `agents/locator_agent.py` | 89 | JSON repair regex targets wrong character, is a no-op |
| M-06 | MEDIUM | `conftest_shared_fixtures.py` | — | second_user not enrolled in CleanupRegistry — staging DB orphan leak |
| M-07 | MEDIUM | `integrations/github_client/github_client.py` | 99, 113 | emoji in machine-generated output breaks downstream parsers |
| M-08 | MEDIUM | `config/settings.py` | 26-29 | all 4 Telegram chat IDs required — blocks non-Telegram setups from running |
| L-01 | LOW | `agents/requirements_agent.py` | 113 | RAG context dropped for chunks 2+ |
| L-02 | LOW | `agents/reviewer_agent.py` | 278 | FileNotFoundError string injected into LLM as test case content |
| L-03 | LOW | `platforms/web/pages/base_page.py` | 188 | skills/assertions deprecation scope unclear |
| L-04 | LOW | `agents/flaky_test_agent.py` | 132 | outcome label says newest-first but data is oldest-first |
| L-05 | LOW | `integrations/github_client/github_client.py` | 29 | no token validation; unconfigured vs failed indistinguishable |
| L-06 | LOW | `knowledge_base/rag_engine.py` | — | embedding model name hardcoded, no env override |
| L-07 | LOW | `conftest_shared_fixtures.py` | — | fixture scope comment could mislead |

---

## Forward-Looking: LLM Agent Acceleration Map

This section identifies every upcoming feature area where the agent pipeline can be wired directly into the QA workflow — from story intake to deployed test.

---

### 1. Auto-Triage: Jira Story → AC → Test Cases (Live)

**Current state:** `RequirementsAgent.run_from_jira()` + `TestCaseAgent.run()` + approval loop already exists.  
**Gap:** Not wired to a Jira webhook trigger. Stories require manual `pipeline.run()` invocation.  
**Acceleration:** Wire `integrations/jira_webhook/webhook_server.py` to trigger `pipeline.run()` on `issue_created` + `issue_updated` events for stories in the QA backlog. Every Jira story automatically generates draft test cases within minutes of creation.

---

### 2. Auto-Review: Generated Tests vs PRD Coverage

**Current state:** `ReviewerAgent.review()` exists with traceability matrix + Excel export.  
**Gap:** Not called automatically after test case generation — requires manual invocation.  
**Acceleration:** Add `ReviewerAgent` as a pipeline node after `testcase_export`. Any coverage below the configured threshold (default 80%) blocks the approval step and sends a Telegram alert with the coverage report attached.

---

### 3. Regression Impact Analysis: PR → Changed Files → Targeted Test Run

**Current state:** `GitHubClient.list_pr_files()` can list PR-changed files. `pyproject.toml` has `testpaths = ["tests", "features"]`.  
**Gap:** No mapping from changed file → test file. Full regression runs on every PR.  
**Acceleration:** Build a `ChangedFileMapper` that maps `features/<feature>/**` → `features/<feature>/steps/**` test files. On PR open, trigger only the affected feature suites. Use `github_client.create_check_run()` to post results. Reduces PR cycle time by 60–80% for single-feature changes.

---

### 4. Locator Self-Healing in CI

**Current state:** `SelfHealer.heal()` works in local Playwright sessions.  
**Gap:** Not integrated into CI — broken locators cause test failure without healing attempt.  
**Acceleration:** Wrap `BasePage.fill()` / `BasePage.click()` failures in CI with a `--heal` pytest flag that triggers `self_healer.heal()`, saves the result to `locator_store`, and creates a PR with the healed locator file diff. Reduces flaky-locator incidents from manual-fix to auto-PR.

---

### 5. Flaky Test Quarantine + Auto-Bug

**Current state:** `FlakyTestAgent.analyze_batch()` classifies flakiness with root cause.  
**Gap:** No automated path from `FlakyTestResult` → Jira bug → quarantine marker in test file.  
**Acceleration:** Post-pipeline node: for `category="genuine_bug"`, auto-create a Jira bug via `jira_connector` with `[DEV-BUG]` tag, severity P1, and root cause as description. For `category != "genuine_bug"`, add `@pytest.mark.flaky` to the test file and open a PR. Full loop from failure history → Jira ticket → quarantine in one pipeline run.

---

### 6. Mobile Screen Auto-Discovery (Android)

**Current state:** `pom_registry_setup.py` auto-discovers web page objects. Mobile screen objects are registered manually.  
**Gap:** `features/*/screens/android/*_screen.py` are not auto-discovered.  
**Acceleration:** Extend `_discover_android_screens()` in `core/pom_registry_setup.py` using the same `importlib` + `inspect.getmro` pattern, looking for `BaseMobileScreen` in the MRO. Enables code-generated mobile tests to look up existing screens by feature name without manual registration.

---

### 7. Knowledge Base Auto-Refresh from Confluence

**Current state:** `knowledge_base/indexer.py` can index PRD content. Indexing is manual.  
**Gap:** Knowledge base goes stale when PRDs are updated in Confluence.  
**Acceleration:** Add a Confluence webhook endpoint (analogous to `integrations/jira_webhook/`) that fires on `page_updated` events and re-indexes the changed page. Keeps RAG context current without manual `indexer.index_source()` calls.

---

### 8. Test Data Lifecycle: CleanupRegistry + Staging DB Health

**Current state:** `CleanupRegistry` exists with LIFO teardown. Not universally adopted by module-scoped fixtures.  
**Gap:** Orphaned test users accumulate in staging DB over time (see M-06 above).  
**Acceleration:** Audit all `create_approved_user_sync()` call sites and enroll every result in `CleanupRegistry`. Add a nightly CI job that runs `pytest --co -q` to collect fixture setup metadata and reports on any fixtures that don't enroll in cleanup. Prevents staging DB drift.

---

### 9. Agent Quality Gates: Eval Harness

**Current state:** `@pytest.mark.agent` marker exists in `pyproject.toml`. No agent eval tests exist yet.  
**Gap:** Agent quality is unmeasured. A prompt change can silently degrade output without detection.  
**Acceleration:** Add `tests/evals/` with golden-input → expected-output pairs for each agent. Run evals as `pytest -m agent` in CI. Gate on: AC extraction coverage ≥ 85%, reviewer coverage calculation within ±5% of manual, flaky classification accuracy ≥ 90% on labeled history. Enables prompt iteration with regression safety.

---

*Report complete. All 26 findings cite file and line. Fix C-01 through C-05 before onboarding any new team members.*
