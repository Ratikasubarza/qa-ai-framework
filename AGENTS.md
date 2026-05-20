# AGENTS.md — QA AI Framework
> Last updated: May 2026 | Owner: Ratikasubarza | Senior QE → AI Engineering

---

## Critical Rules — Read First

1. **NEVER break existing passing tests** — run the affected suite after every change
2. **NEVER hardcode credentials** — use `TestConfig` or test data classes
3. **NEVER use system Python** — always use `./venv/bin/python3.11`
4. **NEVER change folder structure** without updating all imports
5. **ALWAYS commit after each milestone** — git add → commit → push

---

## Project Overview

AI-powered QA automation framework for **Hono** (app-dev.thehono.com).
Combines LLM agents (OpenRouter/Claude) + Playwright + Appium + LangGraph orchestration.

| Target | Value |
|--------|-------|
| Mobile app | `app.thehono.development` (Flutter Android) |
| API | `https://api-dev.thehono.com` |
| Web | `https://app-dev.thehono.com` |
| DB | MySQL `hono_dev` (staging — requires VPN) |

---

## Folder Structure

```
qa-ai-framework/
├── agents/                  # LLM agent implementations (LangGraph nodes)
├── config/                  # TestConfig, APIEndpoints, settings.py (Pydantic)
├── core/                    # Shared infra: agent_state, circuit_breaker, db/, input_sanitizer, self_healer
├── features/                # One folder per product feature
│   └── <feature>/
│       ├── pages/web/       # Web POM — inherits BasePage
│       ├── screens/android/ # Mobile Screen Objects — inherits BaseMobileScreen
│       ├── locators/
│       │   ├── web/         # Runtime Playwright locators (CSS/ARIA strings)
│       │   └── mobile/      # Runtime Appium locators (accessibility IDs, indices)
│       ├── steps/
│       │   ├── api/         # API tests (httpx / SchemaValidator)
│       │   ├── web/         # Web e2e tests (Playwright / POM)
│       │   └── mobile/      # Mobile e2e tests (Appium / Screen Objects)
│       └── test_data/       # Test data classes — never raw strings in tests
├── knowledge_base/          # RAG engine (ChromaDB) + source prep
├── locators/registry/       # YAML healing metadata per feature (*.web.yaml)
├── integrations/            # External system bridges
│   ├── approval_workflow/   # Async approval schema + feedback handler
│   ├── confluence_client/   # Confluence MCP bridge
│   ├── figma_client/        # Figma MCP bridge
│   ├── github_client/       # GitHub API client
│   ├── jira_client/         # Jira API client
│   ├── jira_webhook/        # Jira webhook server (FastAPI)
│   └── telegram_bot/        # Telegram notification bot
├── orchestrator/            # LangGraph pipeline (pipeline.py)
├── platforms/
│   ├── api/                 # HonoAPIClient (httpx async)
│   ├── web/pages/           # BasePage (Playwright)
│   └── mobile/screens/      # BaseMobileScreen (Appium)
├── reports/                 # Allure, Excel, metrics output
├── scripts/
│   ├── ci_cd/               # CI/CD helper scripts (secret sync, GitHub setup)
│   └── run_demo.py          # Pipeline demo runner
└── skills/
    ├── api/                 # SchemaValidator — canonical API assertion library
    ├── assertions/          # DEPRECATED — api_assertions.py is a stub for SchemaValidator
    ├── base/                # DEPRECATED — ElementInteraction, WaitStrategy, AssertionHelper
    └── testing/             # Shared test helpers (assert_required_keys, etc.)
```

---

## Canonical Import Rules (Enforced)

### API Tests
```python
# CORRECT
from skills.api.schema_validator import SchemaValidator
SchemaValidator(response).status_ok().has_key("data").response_time_under(3000)

# FORBIDDEN — deprecated alias, will be removed
from skills.assertions.api_assertions import APIAssertions
```

### Web Tests (Playwright)
```python
# CORRECT — use the Page Object, never raw page.click() in tests
from features.login.pages.web.login_page import LoginPage
LoginPage(page).open().login(email, password).assert_login_success()

# FORBIDDEN — skills/base/ must not be imported directly in test files
from skills.base.element_interaction import ElementInteraction
from skills.base.wait_strategy import WaitStrategy
from skills.base.assertion_helper import AssertionHelper
```

### Mobile Tests (Appium)
```python
# CORRECT — use the Screen Object
from features.login.screens.android.login_screen import LoginScreen
LoginScreen(driver).ensure_on_login_screen().login(email, password).assert_login_success()

# FORBIDDEN — direct raw driver interaction in test files
from skills.mobile.mobile_interaction import MobileInteraction
```

---

## Test File Conventions

| Rule | Example |
|------|---------|
| Naming | `test_TC_[SUITE]_[NNN]_[snake_description]` |
| Allure — module level only | `pytestmark = [allure.feature("Login"), allure.suite("Web")]` |
| No per-test allure decorators | `@allure.story()` and `@allure.severity()` are forbidden |
| Async API tests | `@pytest.mark.asyncio` + `async def test_` |
| Sync Web/Mobile tests | plain `def test_` |
| Markers | `@pytest.mark.smoke`, `.negative`, `.web`, `.mobile`, `.api` |

---

## Reusable Code — Where to Find

| Need | Location |
|------|----------|
| API client | `platforms/api/httpx_client.py` → `HonoAPIClient` |
| API assertions | `skills/api/schema_validator.py` → `SchemaValidator` |
| DB operations | `core/db/db_client.py` → `DBClient` |
| Create synthetic user | `core/db/test_user_helper.py` → `create_approved_user()` |
| Test config / URLs | `config/test_config.py` → `TestConfig`, `APIEndpoints` |
| Web base page | `platforms/web/pages/base_page.py` → `BasePage` |
| Mobile base screen | `platforms/mobile/screens/base_mobile_screen.py` → `BaseMobileScreen` |
| Self-healer | `core/self_healer.py` → `self_healer` (used inside BasePage, not in tests) |
| Input sanitization | `core/input_sanitizer.py` → `InputSanitizer` |
| Circuit breaker | `core/circuit_breaker.py` → `CircuitBreaker` |
| LangGraph pipeline | `orchestrator/pipeline.py` |
| Agent contracts | `core/agent_contracts.py` — Pydantic schemas for all agent I/O |
| CMS token | `get_cms_token()` in `features/cms_users/steps/api/conftest.py` |

---

## TDD Flow — Mandatory

1. **Write Gherkin spec** in `gherkin/` folder
2. **Run test** — confirm it FAILS (red)
3. **Implement** the feature or fix
4. **Run test again** — confirm it PASSES (green)
5. **Refactor** if needed, then commit

```bash
PYTHONPATH=. ./venv/bin/python3.11 -m pytest [test_file] -v
```

---

## Feedback Loop — Mandatory

After every file modification:

```bash
# 1. Run affected suite
PYTHONPATH=. ./venv/bin/python3.11 -m pytest [affected_test] -v --tb=short

# 2. Static analysis
./venv/bin/python3.11 -m ruff check . --select E,W,F --ignore E501,E402

# 3. Verify imports
PYTHONPATH=. ./venv/bin/python3.11 -c "from [modified_module] import *; print('OK')"
```

---

## Security Checklist

Before every commit:
- [ ] No hardcoded credentials
- [ ] No hardcoded URLs — use `TestConfig`
- [ ] `.env` not committed (it is in `.gitignore`)
- [ ] No raw DB errors in assertion messages
- [ ] Webhook endpoints require HMAC or Bearer token auth
- [ ] All subprocess paths validated against project root (no path traversal)
- [ ] `[DEV-BUG]` tag used for API contract violations found during testing

---

## API Spec

Stored in `api_spec.yaml` — update when a new endpoint is added.

Endpoints covered:
- `POST /v1/users/login` — user + admin (`resource=admin`)
- `POST /v1/users/register`
- `GET /v1/users/me`
- `GET /v1/users/me/account` + `PUT /v1/users/me/account`
- `GET /v1/users` — CMS list
- `POST /v1/users/:id/approve` / `reject`
- `PUT /v1/users/onboarding`
- `GET /v1/feed` + `GET /v1/topics`
- `POST /v1/auth/refresh` / `forgot-password` / `reset-password` / `resend-email`

---

## Model Configuration

Current: `MODEL_TIER=development` — free models via OpenRouter
Production: set `MODEL_TIER=production` + `ANTHROPIC_API_KEY` to use Claude

See `core/llm_client.py` for the full model list.
