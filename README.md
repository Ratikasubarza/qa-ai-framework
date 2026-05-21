# QA AI Framework — Hono App

AI-powered QA automation framework for the Hono app. Combines pytest + Playwright + Appium with LangGraph AI agents (LLM test case generation, RAG knowledge base, Telegram approval workflow).

**Target:** `app-dev.thehono.com` / `api-dev.thehono.com` / Flutter Android `app.thehono.development`

---

## Prerequisites

- Python 3.11 (`./venv/bin/python3.11` — never system python)
- VPN connection (required for DB operations — `create_approved_user_sync`, onboarding/posts tests)
- Appium server + Android device/emulator (mobile tests only)
- `.env` file with all required keys (copy from `.env.example`)

---

## Setup

```bash
# 1. Enter project directory
cd qa-ai-framework-backup-20260508

# 2. Create virtualenv
python3.11 -m venv venv

# 3. Install dependencies
./venv/bin/pip install -r requirements.txt

# 4. Copy and fill .env
cp .env.example .env
# Fill: OPENROUTER_API_KEY, JIRA_*, TELEGRAM_*, HONO_API_KEY, STAGING_EMAIL, STAGING_PASSWORD

# 5. Install pre-commit hooks
./venv/bin/pre-commit install
```

---

## How to Run Tests

### All API tests (CI-safe, no VPN required for most):
```bash
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/ \
  --ignore=features/login/steps/mobile \
  --ignore=features/login/steps/web \
  --ignore=features/register/steps/mobile \
  --ignore=features/onboarding/steps/mobile \
  -v --tb=short
```

### By marker (P0 smoke only):
```bash
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/ -m "smoke" -v
```

### Single suite:
```bash
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/login/steps/api/ -v
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/register/steps/api/ -v
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/posts/steps/api/ -v
```

### Web tests (requires Playwright + browser):
```bash
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/login/steps/web/ -v
```

### Android tests (requires Appium + device):
```bash
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/login/steps/mobile/ -v
```

**Last run:** `127 passed, 3 xfailed, 18 deselected` (mobile + web excluded in CI API-only runs)

---

## How to Add a New Test Suite

```
features/
└── my_feature/
    ├── __init__.py
    ├── gherkin/api/my_feature_api.feature
    ├── locators/
    │   ├── web/my_feature_web_locators.py
    │   └── mobile/my_feature_android_locators.py
    ├── pages/                  # Playwright POM
    ├── screens/                # Appium POM
    ├── steps/
    │   ├── api/my_feature_api_test.py
    │   ├── web/my_feature_web_test.py
    │   └── mobile/my_feature_android_test.py
    └── test_data/my_feature_test_data.py
```

**Naming:** `test_TC_[SUITE]_[NUM]_description`

**Test file pattern** (follow exactly — no per-test allure decorators):
```python
pytestmark = allure.feature("MyFeature")  # module-level only

@pytest.mark.smoke      # P0
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_XXX_001_happy_path():
    """TC-XXX-001 | Smoke | Short description"""
    ...
```

Marker guide: `@pytest.mark.smoke` (P0) · `@pytest.mark.sanity` (P1) · `@pytest.mark.regression` (P2)

---

## How to Use AI Agents

```bash
# Generate test cases from Jira ticket
PYTHONPATH=. ./venv/bin/python3.11 cli.py generate testcase \
  --feature "Login" --platform api --jira-story HM-123

# Run full pipeline (source_intake → testcase → review → codegen)
PYTHONPATH=. ./venv/bin/python3.11 cli.py pipeline \
  --ticket HM-516 --include-subtasks --platform web

# Export test cases to Excel/CSV
PYTHONPATH=. ./venv/bin/python3.11 cli.py generate testcase \
  --feature "Register" --platform api --export

# Verify LLM connection
PYTHONPATH=. ./venv/bin/python3.11 cli.py smoke
```

---

## Folder Structure

```
.
├── agents/                 # LangGraph agents (test_case, code_gen, reviewer, debug)
├── config/
│   ├── test_config.py      # Automation runtime config, APIEndpoints, Timeouts, ReferenceIDs
│   ├── error_messages.py   # APIErrors, AndroidErrors, ValidationErrors
│   ├── test_data.py        # BoundaryValues, KnownAccounts
│   └── settings.py         # pydantic-settings (loaded from .env)
├── core/
│   ├── llm_client.py       # OpenRouter LLM client
│   ├── telegram_bot.py     # Telegram approval bot (start/stop polling)
│   └── db/                 # DB helpers (requires VPN)
├── features/               # Test suites — one folder per feature
├── knowledge_base/
│   ├── indexer.py          # RAG indexer — reads from sources/
│   ├── rag_engine.py       # ChromaDB retrieval
│   └── vector_store/       # ChromaDB binary files
├── integrations/
│   ├── jira_client/        # Jira REST API client
│   ├── github_client/      # GitHub PR comment client
│   └── figma_client/       # Figma design extraction client
├── orchestrator/
│   └── pipeline.py         # LangGraph Phase 9 full pipeline
├── platforms/
│   ├── api/httpx_client.py # HonoAPIClient
│   ├── web/                # Playwright BasePage POM
│   └── mobile/             # Appium BaseScreen POM
├── skills/
│   ├── assertions/         # APIAssertions, WebAssertions, MobileAssertions
│   └── api/schema_validator.py
├── cli.py                  # CLI entry point
└── pytest.ini
```

See `docs/architecture/framework_maturity_plan.md` for the current config, API client, test data, locator, security, CI, and artifact governance plan.

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `DB connection refused` | Connect to VPN first |
| `401 Unauthorized — intermittent` | Staging MySQL pool exhaustion — retry once |
| `Resend quota 500` | Email quota hit — register tests auto-skip via `skip_on_email_quota()` |
| `Appium SessionNotCreatedException` | Start Appium server: `appium` in terminal |
| `ModuleNotFoundError` | Run with `PYTHONPATH=. ./venv/bin/python3.11 -m pytest ...` |
| `xfail: nationality` | Known DEV-BUG-002 — GET /v1/users/me/account omits nationality key |
| `xfail: verify-email 404` | Known DEV-BUG-001 — GET /v1/users/verify-email returns 404 |
| Python version wrong | Always use `./venv/bin/python3.11`, never system python |
