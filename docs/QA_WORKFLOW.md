# QA AI Framework — Team Workflow Guide

> Version: 1.0 | Target: QA Engineers onboarding to this framework
> App: **Hono** (`app-dev.thehono.com` / `api-dev.thehono.com` / Flutter Android)

---

## 1. Framework Architecture at a Glance

```
                    ┌─────────────────────────────────────┐
                    │          AI Agent Pipeline          │
                    │  (LangGraph — orchestrator/)        │
                    │                                     │
                    │  RequirementsAgent                  │
                    │       ↓                             │
                    │  TestPlanAgent                      │
                    │       ↓                             │
                    │  TestCaseAgent v2.1.0               │
                    │       ↓                             │
                    │  TestCodeGenAgent                   │
                    └─────────────────────────────────────┘
                                    │
                    ┌───────────────┼────────────────┐
                    ▼               ▼                ▼
            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │  Web Tests   │ │ Mobile Tests │ │  API Tests   │
            │  Playwright  │ │   Appium     │ │   httpx      │
            │  POM-based   │ │  Screen Obj  │ │ SchemaValid. │
            └──────────────┘ └──────────────┘ └──────────────┘
```

---

## 2. Golden Rules — Memorize Before Writing a Test

| # | Rule | Why |
|---|------|-----|
| 1 | **Never** import from `skills.base.*` in test files | Deprecated — breaks CI |
| 2 | **Never** call `driver.driver.find_elements()` in test files | Belongs in screen objects only |
| 3 | **Never** call `page.click()` / `page.fill()` directly in test files | Belongs in page objects only |
| 4 | **Always** use `./venv/bin/python3.11` | Never system Python |
| 5 | **Always** add `pytestmark` at the module level | No per-test allure decorators |
| 6 | **Never** hardcode URLs, emails, passwords | Use `TestConfig` and test data classes |

---

## 3. Project Layout — Where Things Live

```
qa-ai-framework/
│
├── agents/                  # AI agents (LLM-powered)
│   ├── requirements_agent.py   # Extracts AC from Jira / Confluence PRD
│   ├── test_plan_agent.py      # Generates test plan (techniques + scenarios)
│   └── test_case_agent.py      # Generates test cases v2.1.0
│
├── features/                # One folder per product feature
│   └── <feature_name>/
│       ├── locators/
│       │   ├── web/            # CSS/ARIA selectors (strings)
│       │   └── mobile/         # Accessibility IDs, indices
│       ├── pages/
│       │   └── web/            # Web Page Objects (inherits BasePage)
│       ├── screens/
│       │   └── android/        # Mobile Screen Objects (inherits BaseMobileScreen)
│       ├── steps/
│       │   ├── web/            # Web e2e tests (Playwright)
│       │   ├── mobile/         # Mobile e2e tests (Appium)
│       │   └── api/            # API tests (httpx)
│       └── test_data/          # Test data classes (no raw strings in tests)
│
├── platforms/
│   ├── web/pages/base_page.py        # BasePage — all web POMs inherit this
│   └── mobile/screens/base_mobile_screen.py  # BaseMobileScreen — all screen objects
│
├── core/
│   ├── agent_contracts.py    # Pydantic schemas for all agent I/O
│   ├── llm_client.py         # OpenRouter / Anthropic LLM client
│   ├── self_healer.py        # Locator self-healing (used inside BasePage)
│   └── db/
│       ├── db_client.py      # MySQL DBClient
│       └── test_user_helper.py  # create_approved_user_sync()
│
├── skills/
│   ├── api/schema_validator.py   # ✅ Canonical API assertion library
│   └── assertions/               # mobile_assertions.py (used by screen objects)
│
├── config/
│   └── test_config.py        # TestConfig, APIEndpoints, Timeouts
│
├── orchestrator/
│   └── pipeline.py           # LangGraph 14-node pipeline
│
└── reports/
    ├── test_plans/           # Generated test plans (CSV)
    └── test_cases/           # Generated test cases (CSV)
```

---

## 4. How to Write a Web Test (Step by Step)

### Step 1 — Check if a Page Object exists

```bash
ls features/<feature>/pages/web/
```

If it doesn't exist, create it first (Step 2). If it does, skip to Step 4.

### Step 2 — Create the Locators file

```python
# features/<feature>/locators/web/<feature>_web_locators.py

FEATURE_URL = "/<path>"

SOME_INPUT   = 'input[data-testid="some-input"]'
SUBMIT_BTN   = '[data-testid="submit-button"]'
ERROR_MSG    = '[data-testid="error-message"]'
```

### Step 3 — Create the Page Object

```python
# features/<feature>/pages/web/<feature>_page.py

from playwright.sync_api import Page
from platforms.web.pages.base_page import BasePage
from features.<feature>.locators.web.<feature>_web_locators import (
    FEATURE_URL, SOME_INPUT, SUBMIT_BTN, ERROR_MSG,
)

class FeaturePage(BasePage):
    URL = FEATURE_URL

    def open(self) -> "FeaturePage":
        self.goto()
        self.wait_for(SOME_INPUT)
        return self

    def enter_value(self, text: str) -> "FeaturePage":
        self.fill(SOME_INPUT, text, description="Some input")
        return self

    def submit(self) -> "FeaturePage":
        self.click(SUBMIT_BTN, description="Submit button")
        return self

    def has_error(self) -> bool:
        return self.is_visible(ERROR_MSG)

    def assert_success(self) -> "FeaturePage":
        self.wait_for_url("/expected-path")
        return self

    def assert_error_visible(self) -> "FeaturePage":
        self.assert_that.element_visible(ERROR_MSG, "Error message")
        return self
```

### Step 4 — Write the Test

```python
# features/<feature>/steps/web/<feature>_web_test.py

import allure
import pytest
from playwright.sync_api import Page
from features.<feature>.pages.web.<feature>_page import FeaturePage
from features.<feature>.test_data.<feature>_test_data import FeatureTestData

pytestmark = [allure.feature("<Feature Name>"), allure.suite("Web")]


def test_TC_WEB_001_happy_path(page: Page):
    """TC-WEB-001 | Smoke | Description of what this tests"""
    (
        FeaturePage(page).open()
        .enter_value(FeatureTestData.VALID_VALUE)
        .submit()
        .assert_success()
    )


def test_TC_WEB_002_negative_case(page: Page):
    """TC-WEB-002 | Negative | Description"""
    (
        FeaturePage(page).open()
        .enter_value(FeatureTestData.INVALID_VALUE)
        .submit()
        .assert_error_visible()
    )
```

---

## 5. How to Write a Mobile Test (Step by Step)

### Step 1 — Check if a Screen Object exists

```bash
ls features/<feature>/screens/android/
```

### Step 2 — Create the Locators file

```python
# features/<feature>/locators/mobile/<feature>_android_locators.py
from appium.webdriver.common.appiumby import AppiumBy

FIELD_INDEX   = 0     # EditText index (Flutter widgets)
BUTTON_AID    = "Button accessibility label"
SUCCESS_TEXT  = "Expected text after action"
```

### Step 3 — Create the Screen Object

```python
# features/<feature>/screens/android/<feature>_screen.py

from appium.webdriver.common.appiumby import AppiumBy
from platforms.mobile.screens.base_mobile_screen import BaseMobileScreen
from features.<feature>.locators.mobile.<feature>_android_locators import (
    FIELD_INDEX, BUTTON_AID, SUCCESS_TEXT,
)

class FeatureScreen(BaseMobileScreen):

    def enter_field(self, value: str) -> "FeatureScreen":
        self.fill_by_index(FIELD_INDEX, value, description="Field label")
        return self

    def tap_button(self) -> "FeatureScreen":
        self.tap(AppiumBy.ACCESSIBILITY_ID, BUTTON_AID, description="Button label")
        return self

    def assert_success(self) -> "FeatureScreen":
        assert self.wait_for_text_in_source(SUCCESS_TEXT, timeout=10), \
            f"Expected '{SUCCESS_TEXT}' but not found"
        return self
```

### Step 4 — Write the Test

```python
# features/<feature>/steps/mobile/<feature>_android_test.py

import pytest
from features.<feature>.screens.android.<feature>_screen import FeatureScreen
from features.<feature>.test_data.<feature>_test_data import FeatureTestData

pytestmark = [pytest.mark.mobile]


def test_TC_MOB_001_happy_path(android_driver):
    """TC-MOB-001 | Smoke | Description"""
    FeatureScreen(android_driver).enter_field(FeatureTestData.VALID_VALUE).tap_button().assert_success()
```

---

## 6. How to Write an API Test

```python
# features/<feature>/steps/api/<feature>_api_test.py

import pytest
from skills.api.schema_validator import SchemaValidator
from platforms.api.httpx_client import HonoAPIClient
from features.<feature>.test_data.<feature>_test_data import FeatureTestData

pytestmark = [pytest.mark.api]


@pytest.mark.asyncio
async def test_TC_API_001_get_resource_returns_200():
    """TC-API-001 | Smoke | GET /resource returns 200 with expected schema"""
    async with HonoAPIClient() as client:
        resp = await client.get("/v1/resource", token=FeatureTestData.VALID_TOKEN)
    (
        SchemaValidator(resp)
        .status_ok()
        .has_key("data")
        .response_time_under(3000)
    )
```

---

## 7. AI Agent Pipeline — How to Generate Tests from PRD

### Full Pipeline (PRD + Jira → Test Plan + Test Cases)

```bash
PYTHONPATH=. python3.11 -c "
import asyncio, datetime
from pathlib import Path
from agents.requirements_agent import requirements_agent
from agents.test_plan_agent import test_plan_agent
from agents.test_case_agent import test_case_agent
from core.agent_contracts import TestCaseAgentInput
from skills.reporting.excel_writer import ExcelWriter

PRD_URL   = 'https://thehono.atlassian.net/wiki/...'
JIRA_KEYS = ['HM-500', 'HM-501']
PLATFORMS = ['web', 'api']
RUN_ID    = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

# Step 1: Extract ACs
prd_result = requirements_agent.run_from_confluence(prd_url=PRD_URL, jira_story_keys=JIRA_KEYS)
feature_name = prd_result['feature']
ac_list      = prd_result['acceptance_criteria']

# Step 2: Test Plan → reports/test_plans/
tp_output = test_plan_agent.create_test_plan({
    'feature_name': feature_name,
    'ticket_id': JIRA_KEYS[0],
    'acceptance_criteria': ac_list,
    'description': prd_result.get('prd_title', ''),
    'platforms': PLATFORMS,
})
test_plan_agent.save_report(tp_output, feature_name, RUN_ID)

# Step 3: Test Cases → reports/test_cases/
async def run():
    inp = TestCaseAgentInput(
        feature=feature_name,
        description=prd_result.get('prd_title', ''),
        platforms=PLATFORMS,
        acceptance_criteria=ac_list,
        confluence_page_url=PRD_URL,
        jira_story_keys=JIRA_KEYS,
    )
    return await test_case_agent.run(inp, require_approval=False)

tc_output = asyncio.run(run())
writer = ExcelWriter(output_dir='reports/test_cases')
writer.write_csv(tc_output)
"
```

Outputs:
- `reports/test_plans/<feature>_test_plan_<date>.csv`
- `reports/test_cases/test_cases_<date>.csv`

---

## 8. Running Tests

```bash
# All web tests
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/ -m web -v

# All mobile tests
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/ -m mobile -v

# All API tests
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/ -m api -v

# One specific file
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/login/steps/web/login_web_app_test.py -v

# Smoke only
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/ -m smoke -v

# With Allure report
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/ --alluredir=reports/allure-results
allure serve reports/allure-results
```

---

## 9. Test Naming Convention

| Layer | Pattern | Example |
|-------|---------|---------|
| Web | `test_TC_WEB_NNN_snake_description` | `test_TC_WEB_001_login_button_disabled_when_empty` |
| Mobile | `test_TC_MOB_NNN_snake_description` | `test_TC_MOB_001_login_valid_credentials` |
| Feature mobile | `test_TC_MOB_<FEAT>_NNN_...` | `test_TC_MOB_ONB_001_complete_onboarding_flow` |
| API | `test_TC_API_NNN_snake_description` | `test_TC_API_001_login_returns_token` |

---

## 10. BasePage Methods Reference (Web)

All page objects inherit these — never call `page.*` directly in tests.

| Method | Signature | Description |
|--------|-----------|-------------|
| `goto()` | `goto(path=None)` | Navigate to page URL |
| `fill()` | `fill(selector, value, description="")` | Fill an input |
| `click()` | `click(selector, description="")` | Click an element |
| `wait_for()` | `wait_for(selector, timeout=8000)` | Wait for element visibility |
| `wait_for_url()` | `wait_for_url(fragment)` | Wait for URL to contain fragment |
| `is_visible()` | `is_visible(selector) → bool` | Check visibility |
| `is_enabled()` | `is_enabled(selector) → bool` | Check enabled state |
| `get_text()` | `get_text(selector) → str` | Get element text |
| `assert_that` | property → `WebAssertions` | Fluent assertion chain |

---

## 11. BaseMobileScreen Methods Reference (Mobile)

| Method | Signature | Description |
|--------|-----------|-------------|
| `tap()` | `tap(by, value, description="")` | Tap by locator |
| `fill()` | `fill(by, value, text, description="")` | Fill by locator |
| `fill_by_index()` | `fill_by_index(index, text)` | Fill EditText by position index |
| `tap_accessibility()` | `tap_accessibility(label)` | Tap by accessibility ID |
| `scroll_down()` | `scroll_down()` | Scroll down |
| `hide_keyboard()` | `hide_keyboard()` | Dismiss keyboard |
| `wait_for_text_in_source()` | `wait_for_text_in_source(text, timeout=10.0) → bool` | Poll page source |
| `wait_for_element()` | `wait_for_element(by, value, timeout=10)` | Wait for element |
| `is_visible()` | `is_visible(by, value, timeout=5) → bool` | Check visibility |
| `get_page_source()` | `get_page_source() → str` | Get XML page source |
| `assert_that` | property → `MobileAssertions` | Fluent assertion chain |

---

## 12. SchemaValidator Reference (API)

```python
from skills.api.schema_validator import SchemaValidator

SchemaValidator(response)
    .status_ok()                        # status == 200
    .status(201)                        # custom status
    .has_key("data")                    # key exists in body
    .has_keys(["id", "email"])          # all keys exist
    .key_equals("status", "active")     # key has exact value
    .response_time_under(3000)          # response time < 3000ms
    .schema_matches({"id": int, ...})   # type validation
```

---

## 13. Feedback Loop After Every Change

```bash
# 1. Run affected tests
PYTHONPATH=. ./venv/bin/python3.11 -m pytest <affected_test_file> -v --tb=short

# 2. Lint check
./venv/bin/python3.11 -m ruff check . --select E,W,F --ignore E501,E402

# 3. Import verification
PYTHONPATH=. ./venv/bin/python3.11 -c "from <modified_module> import *; print('OK')"
```

---

## 14. Config Reference

```python
from config.test_config import TestConfig, APIEndpoints, Timeouts

TestConfig.WEB_APP_URL          # "https://app-dev.thehono.com"
TestConfig.API_BASE_URL         # "https://api-dev.thehono.com"
TestConfig.ANDROID_PACKAGE      # Flutter app package
TestConfig.ANDROID_DEVICE       # Device name from AVD/USB
Timeouts.PAGE_LOAD_MS           # 15000
APIEndpoints.LOGIN              # "/v1/users/login"
APIEndpoints.REGISTER           # "/v1/users/register"
```

---

## 15. Common Mistakes & Fixes

| Mistake | Fix |
|---------|-----|
| `from skills.base.element_interaction import ElementInteraction` | Use `BasePage.fill()` / `BasePage.click()` |
| `page.click(selector)` directly in test | Use `FeaturePage(page).some_action()` |
| `driver.driver.find_elements(...)` in test | Use `ScreenObject.fill_by_index()` |
| `page.goto(f"{page.url}/feed")` | Use `FeedPage(page).open()` |
| `@allure.story()` per test function | Module-level `pytestmark` only |
| Hardcoded email `"user@test.com"` | `LoginTestData.VALID_EMAIL` |
| `driver.driver.page_source` | `driver.get_page_source()` |
| `MobileAssertions(driver).element_disabled_by_accessibility(...)` in test | `ScreenObject.assert_button_disabled()` |
