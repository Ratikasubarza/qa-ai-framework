# How to Add a New Test Suite

Follow this TDD flow exactly. No exceptions.

## Step 1 — Create the folder structure

```bash
# Replace <feature> with your feature name (snake_case)
mkdir -p features/<feature>/gherkin/api
mkdir -p features/<feature>/steps/api
mkdir -p features/<feature>/test_data
mkdir -p features/<feature>/locators/web     # web only
mkdir -p features/<feature>/locators/mobile  # android only
```

## Step 2 — Write the Gherkin spec first (TDD red)

Create `features/<feature>/gherkin/api/<feature>_api.feature`:

```gherkin
Feature: <Feature Name> API

  Background:
    Given the API is available

  Scenario: TC-<SUITE>-001 — Happy path description
    Given a valid authenticated user
    When they POST to the <feature> endpoint with valid payload
    Then the response status is 200
    And the response body contains expected fields

  Scenario: TC-<SUITE>-002 — Negative: missing required field
    Given a valid authenticated user
    When they POST with missing required field
    Then the response status is 400
```

Key rules:
- No `/v1/` URLs in Gherkin — behavior-driven language only
- Use `Given/When/Then` strictly
- One scenario per test case

## Step 3 — Create test data

Create `features/<feature>/test_data/<feature>_test_data.py`:

```python
import os
import time
from dataclasses import dataclass, field
from dotenv import load_dotenv
from core.test_data.base_builder import PayloadBuilder
from config.test_data import BoundaryValues
from config.test_config import APIEndpoints
from skills.data.data_generator import DataGenerator

load_dotenv(dotenv_path=".env")


@dataclass
class <Feature>Payload(PayloadBuilder):
    # Add fields here using DataGenerator for unique values
    email: str = field(default_factory=lambda: DataGenerator.unique_email("<feature>"))

    @classmethod
    def valid(cls) -> "<Feature>Payload":
        return cls()


class <Feature>TestData:
    @staticmethod
    def valid_payload() -> dict:
        return DataGenerator.valid_register_payload()  # or custom dict

    # Security payloads from DataGenerator
    SQL_INJECTION_VARIANTS = DataGenerator.sql_injection_strings()
    XSS_VARIANTS = DataGenerator.xss_strings()
```

## Step 4 — Write the test file (still red)

Create `features/<feature>/steps/api/<feature>_api_test.py`:

```python
"""
<Feature> API Test — PUT/POST /v1/<feature>
Tests: happy path, validation, auth, boundary, security
"""
import pytest
import pytest_asyncio
import httpx
from config.test_config import TestConfig, APIEndpoints
from features.<feature>.test_data.<feature>_test_data import <Feature>TestData
from skills.auth.auth_helper import AuthHelper

pytestmark = [pytest.mark.api, pytest.mark.asyncio]


@pytest.fixture
async def auth_header():
    token = AuthHelper.get_user_token()
    return AuthHelper.build_auth_header(token)


@pytest.mark.smoke
async def test_TC_<SUITE>_001_happy_path(auth_header):
    """Happy path: valid payload returns 200."""
    payload = <Feature>TestData.valid_payload()
    async with httpx.AsyncClient(
        base_url=TestConfig.API_URL,
        headers={"x-api-key": TestConfig.API_KEY},
    ) as client:
        resp = await client.put(
            APIEndpoints.<FEATURE_ENDPOINT>,
            json=payload,
            headers=auth_header,
        )
    assert resp.status_code == 200
```

Naming convention: `test_TC_[SUITE]_[NUM]_[description]`

## Step 5 — Run tests — confirm RED

```bash
PYTHONPATH=. ./venv/bin/python3.11 -m pytest \
  features/<feature>/steps/api/<feature>_api_test.py -v --tb=short
```

Expected: ImportError or AssertionError (endpoint not configured yet).

## Step 6 — Implement / configure

- Add endpoint to `config/test_config.py → APIEndpoints`
- Implement any missing fixture logic
- Run again — should turn GREEN

## Step 7 — Static analysis

```bash
./venv/bin/python3.11 -m ruff check features/<feature>/ --select E,W,F --ignore E501,E402
PYTHONPATH=. ./venv/bin/python3.11 -c "from features.<feature>.test_data.<feature>_test_data import *; print('OK')"
```

## Step 8 — Add to CI pipeline

Edit `.github/workflows/qa-pipeline.yml` → `api-tests` job:

```yaml
PYTHONPATH=. ./venv/bin/python3.11 -m pytest \
  ...existing tests... \
  features/<feature>/steps/api/<feature>_api_test.py \
  --junit-xml=reports/junit/api-results.xml \
  -v --tb=short --timeout=30
```

## Step 9 — Commit

```bash
git add features/<feature>/ config/test_config.py .github/workflows/
git commit -m "feat: <feature> API test suite — TC-<SUITE>-001 to TC-<SUITE>-XXX"
git push origin <branch>
```

## Checklist before PR

- [ ] Gherkin written before test code
- [ ] Red state confirmed before implementation
- [ ] No hardcoded URLs or credentials
- [ ] All test functions have `@pytest.mark` decorators
- [ ] `test_data` uses `DataGenerator` / `BoundaryValues` / `ReferenceIDs`
- [ ] Syntax check passed (`py_compile`)
- [ ] Import check passed
- [ ] All tests green locally
