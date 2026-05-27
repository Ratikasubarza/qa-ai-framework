# QA AI Framework — Runbook

**Owner:** Ratikasubarza | **Last updated:** May 2026  
**Stack:** Python 3.11 · pytest · httpx · Playwright · Appium · LangGraph · ChromaDB

---

## 1. Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11 | `brew install python@3.11` |
| Node.js | 18+ | Required for Playwright browsers |
| MySQL client | any | Only needed if running DB-backed fixtures |
| VPN | — | **Required** to reach staging DB and `api-dev.thehono.com` |

---

## 2. First-Time Setup

```bash
# Clone repo and enter it
git clone <repo-url> qa-ai-framework
cd qa-ai-framework

# Create virtualenv with Python 3.11 (never use system Python)
python3.11 -m venv venv
source venv/bin/activate       # or: . venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for web tests)
./venv/bin/python3.11 -m playwright install chromium

# Copy env template and fill in secrets
cp .env.example .env
# Then open .env in your editor and set all required vars (see section 3)
```

---

## 3. Environment Variables

Copy `.env.example` → `.env`. Variables marked **Required** must be set before any test will pass.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HONO_API_URL` | No | `https://api-dev.thehono.com` | Staging API base URL |
| `HONO_API_KEY` | **Yes** | — | x-api-key header value for all API requests |
| `DB_HOST` | **Yes** | — | MySQL host (VPN required) |
| `DB_PORT` | No | `3306` | MySQL port |
| `DB_USER` | **Yes** | — | MySQL user |
| `DB_PASSWORD` | **Yes** | — | MySQL password |
| `DB_NAME` | **Yes** | — | Database name (`hono_dev`) |
| `DB_SSL_CA_PATH` | No | — | Path to SSL CA cert for DB connection |
| `STAGING_EMAIL` | **Yes** | — | Known staging account email (used by feed tests) |
| `STAGING_PASSWORD` | **Yes** | — | Known staging account password |
| `STAGING_CMS_EMAIL` | **Yes** | — | CMS admin email |
| `STAGING_CMS_PASSWORD` | **Yes** | — | CMS admin password |
| `TEST_ADMIN_TOKEN` | **Yes** | — | Pre-issued admin JWT. **Never commit a real value.** Set in CI secrets. |
| `TEST_EMAIL_DOMAIN` | No | `mailinator.com` | Email domain for synthetic test users |
| `TEST_KNOWN_EMAIL_B` | No | auto | Second known account email |
| `TEST_KNOWN_PHONE_A` | No | auto | Known account phone A |
| `TEST_KNOWN_PHONE_B` | No | auto | Known account phone B |
| `TEST_USER_PASSWORD` | No | `TestPass123!` | Password used when creating synthetic users |
| `OPENROUTER_API_KEY` | **Yes (agents)** | — | LLM API key (OpenRouter) |
| `ANTHROPIC_API_KEY` | No | — | Used when `MODEL_TIER=production` |
| `MODEL_TIER` | No | `development` | `development` (free models) or `production` (Claude) |
| `WEB_APP_URL` | No | `https://app-dev.thehono.com` | Staging web app URL |
| `CMS_URL` | No | `https://cms-dev.thehono.com` | CMS URL |
| `TEST_ENV` | No | `staging` | `staging` or `production` |
| `RUN_ID` | No | auto | Identifies the test run; used in cleanup registry |

---

## 4. Running Tests

All commands use the venv Python. Run from the repo root.

### Quick reference

```bash
# Smoke — fastest pass/fail signal (all platforms)
PYTHONPATH=. ./venv/bin/python3.11 -m pytest -m "smoke" -v --tb=short

# API smoke only
PYTHONPATH=. ./venv/bin/python3.11 -m pytest -m "smoke and api" -v --tb=short

# Full API regression
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/ -m "api" -v --tb=short

# Single feature
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/auth/steps/api/ -v --tb=short

# Single test
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/auth/steps/api/auth_api_test.py::test_TC_AUTH_001_login_success -v

# Skip preflight check (when staging health check blocks you intentionally)
PYTHONPATH=. ./venv/bin/python3.11 -m pytest -m "smoke and api" --skip-preflight -v

# With Allure report generation
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/ -m "api" --alluredir=reports/allure_results
./venv/bin/allure serve reports/allure_results
```

### Available markers

| Marker | Meaning |
|--------|---------|
| `smoke` | Critical happy-path — run first, must be green before merging |
| `negative` | Error-path tests (4xx, invalid input) |
| `api` | API layer tests (httpx, no browser) |
| `web` | Playwright web tests |
| `mobile` | Appium mobile tests |

Combine markers with `and`/`or`: `-m "smoke and api"`, `-m "api and negative"`.

---

## 5. Understanding Test Results

| Result | Meaning | Action |
|--------|---------|--------|
| `PASSED` | Test assertion succeeded | — |
| `FAILED` | Assertion wrong or exception | Read the traceback; likely a real bug |
| `ERROR` | Setup/teardown crashed before test ran | Check fixture; look for DB or API connectivity issues |
| `SKIPPED` | `pytest.skip()` called | Usually email-quota or missing env var; check skip message |
| `XFAIL` | Expected failure | If it passes (`XPASS`), the bug was fixed — remove the marker |

**Preflight failure** (`[PREFLIGHT FAIL]`): Staging API is unreachable. Connect to VPN or wait for staging to recover. Run with `--skip-preflight` to bypass.

**502/503 errors**: Transient staging infrastructure noise. The framework retries 3× automatically (2s, 4s backoff). If they still appear after retry, staging is degraded — wait and re-run.

**`[DEV-BUG]` in test file**: The test is accepting a non-ideal status code because the API has a known contract violation. These are tracked to be fixed by the dev team, not the QA team.

---

## 6. Fixture Patterns

There are exactly **two** approved patterns for auth fixtures. Use the right one.

### Pattern A — Module-scoped async (canonical)

Use for: token/session fixtures shared across all tests in a module.

```python
import pytest
from platforms.api.httpx_client import HonoAPIClient
from config.test_config import APIEndpoints

@pytest.fixture(scope="module")
async def my_token(my_user) -> str:
    async with HonoAPIClient() as client:
        resp = await client.post(APIEndpoints.LOGIN, json={
            "email":    my_user["email"],
            "password": my_user["password"],
        })
    data = resp.json()
    body = data.get("data", data)
    return body.get("accessToken") or body.get("token", "")
```

> Do **not** use `@pytest_asyncio.fixture` — `asyncio_mode="auto"` makes it redundant.

### Pattern B — Function-scoped sync wrapper

Use for: fixtures that must be fresh per test (e.g., a token tied to a user whose state changes during the test).

```python
import asyncio
import pytest
from platforms.api.httpx_client import HonoAPIClient
from config.test_config import APIEndpoints

@pytest.fixture(scope="function")
def my_token(my_user) -> str:
    async def _login():
        async with HonoAPIClient() as client:
            return await client.post(APIEndpoints.LOGIN, json={
                "email":    my_user["email"],
                "password": my_user["password"],
            })
    resp = asyncio.run(_login())
    data = resp.json()
    body = data.get("data", data)
    return body.get("accessToken") or body.get("token", "")
```

> Use this pattern when the test mutates user state (e.g., deactivate, unfollow) between assertion steps.

---

## 7. Adding New Tests

1. **Identify the feature folder** under `features/<feature>/steps/api/`.  
   If the feature folder doesn't exist, copy `features/_template/` and rename it.

2. **Create the test file** named `<feature>_api_test.py` with:
   ```python
   pytestmark = [allure.feature("FeatureName"), allure.suite("API")]
   ```

3. **Write the test function**:
   ```python
   @pytest.mark.smoke
   @pytest.mark.api
   async def test_TC_XYZ_001_happy_path(my_token):
       """TC-XYZ-001 | Smoke | Description"""
       async with HonoAPIClient() as client:
           client.set_auth_token(my_token)
           resp = await client.get(APIEndpoints.MY_ENDPOINT)
       SchemaValidator(resp).status_ok().has_key("data").response_time_under(3000)
   ```

4. **Run the new test** to confirm it is green:
   ```bash
   PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/<feature>/steps/api/<feature>_api_test.py -v
   ```

5. **Naming rules:**
   - File: `<feature>_api_test.py`
   - Function: `test_TC_[SUITE]_[NNN]_[snake_description]`
   - No per-test `@allure.story()` or `@allure.severity()` — module-level `pytestmark` only.

---

## 8. AI Pipeline (LangGraph)

The AI pipeline converts Jira stories into test cases via a 14-node LangGraph graph.

```bash
# Run full pipeline (reads from Jira, generates test cases, sends Telegram approval)
PYTHONPATH=. ./venv/bin/python3.11 scripts/run_demo.py

# Run with a specific story key
PYTHONPATH=. ./venv/bin/python3.11 -c "
from orchestrator.pipeline import run_pipeline
run_pipeline(story_key='HONO-123')
"
```

**Approval workflow:** After generation, the pipeline sends a Telegram message with APPROVE / REJECT buttons. The test architect reviews and approves. On approval, test code is generated and a GitHub PR is opened automatically.

**Nodes (in order):**

| Node | What it does |
|------|-------------|
| `node_fetch_story` | Pulls Jira story + AC |
| `node_enrich_context` | Adds RAG context from ChromaDB |
| `node_generate_cases` | LLM generates test scenarios |
| `node_skill_gap` | Checks coverage vs AC |
| `node_debug` | Flags low-confidence test cases |
| `node_review` | Second LLM pass for quality |
| `node_approval` | Sends Telegram approval request |
| `node_generate_code` | Converts approved cases to pytest |
| `node_pr_open` | Opens GitHub PR with generated code |
| … | (+ 5 supporting nodes) |

---

## 9. CI/CD

Tests run on GitHub Actions on every PR and on-demand.

| Workflow | Trigger | What runs |
|----------|---------|-----------|
| `test-api-smoke.yml` | PR open/push | `smoke and api` markers |
| `test-api-full.yml` | Manual / nightly | All API tests |
| `pipeline-demo.yml` | Manual | AI pipeline demo run |

Read CI results:
- Green check: all smoke tests passed
- Red X on `test-api-smoke`: look at the Actions log, filter for `FAILED` lines
- `ERROR` in collection phase: usually a missing env secret — check repo Settings → Secrets

---

## 10. Troubleshooting

**Problem: `AssertionError: HONO_API_KEY is required`**  
→ Set `HONO_API_KEY` in `.env` or export it in your shell.

**Problem: `[PREFLIGHT FAIL] Cannot reach staging`**  
→ Connect to VPN. Staging DB and API are not reachable without it.

**Problem: `RuntimeError: There is no current event loop`**  
→ An async fixture is scoped to `function` using `@pytest_asyncio.fixture`. Change to Pattern B (sync wrapper with `asyncio.run()`).

**Problem: `sqlalchemy.exc.OperationalError` / `Can't connect to MySQL`**  
→ Check VPN, then verify `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` in `.env`.

**Problem: 502/503 errors not going away after retry**  
→ Staging is degraded. Check with the backend team or wait ~15 min and re-run.

**Problem: `SKIP — email quota exceeded`**  
→ Mailinator free tier hit its limit. Use a private domain: set `TEST_EMAIL_DOMAIN` to your private inbox domain.

**Problem: Allure report shows no tests**  
→ Run `pytest` with `--alluredir=reports/allure_results` then `allure serve reports/allure_results`.

**Problem: `ModuleNotFoundError` on import**  
→ Ensure you're running with `PYTHONPATH=. ./venv/bin/python3.11 -m pytest`, not the system Python.

---

## 11. Contacts & Escalation

| Area | Owner | How to reach |
|------|-------|-------------|
| Test framework / fixtures | Ratikasubarza | Telegram / GitHub @Ratikasubarza |
| Staging API / backend | Dev team | `#backend-staging` Slack channel |
| CI/CD pipeline | DevOps | `#devops` Slack channel |
| API contract violations (`[DEV-BUG]`) | Dev team + QA lead | Jira ticket + `#qa-bugs` Slack |
| Jira / Confluence access | Project manager | `#project-mgmt` Slack |

---

## 12. Known API Contract Violations (DEV-BUG)

These tests currently accept a workaround status code while the dev team fixes the API.

| Test | Endpoint | Expected | Actual | JIRA |
|------|----------|----------|--------|------|
| TC-AUTH-005 | `POST /v1/auth/forgot-password` | 200 (no account disclosure) | 422 | NOKUNPROC |
| TC-PRIV-003 | `POST /v1/users/{uuid}/follow` | 404 | 422 | NOKUNPROC |
| TC-RS-010 | `POST /v1/search/recent` | 401 | 404 (not deployed) | TBD |
| TC-RS-014 | `DELETE /v1/search/recent/{id}` | 401 | 404 (not deployed) | TBD |

When the API team deploys a fix, remove the extra status code from `status_in(...)` and delete the `[DEV-BUG]` comment in the test file.
