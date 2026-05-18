# How to Debug Test Failures

## Quick triage

```bash
# Run just the failing test with full output
PYTHONPATH=. ./venv/bin/python3.11 -m pytest \
  features/<feature>/steps/api/<test_file>.py::<test_name> \
  -v --tb=long -s
```

## Using the Debug Agent CLI

```bash
PYTHONPATH=. ./venv/bin/python3.11 cli.py debug \
  --test-file features/login/steps/api/login_api_test.py \
  --error "AssertionError: expected 200 got 401" \
  --platform api
```

Returns: severity, root cause classification, steps to reproduce, suggested fix.

## Common failure patterns

### HTTP 401 — Unauthorized
- Staging credentials expired or wrong
- Token not passed in header
- Check: `STAGING_EMAIL` / `STAGING_PASSWORD` in `.env`
- Check: CMS token uses `resource="admin"` in payload

### HTTP 500 with "email sending quota"
- Resend daily email quota hit
- Test will auto-skip (pytest.skip injected by `test_user_helper.py`)
- Wait until midnight SGT for quota reset

### Import errors
- Missing `PYTHONPATH=.` prefix
- Module moved or renamed — check imports

### `AssertionError: token not found in response`
- API response structure changed
- Check: `data.get("data", data).get("accessToken")` — may be nested differently
- Tag as `[DEV-BUG]` if API spec doesn't match

### Playwright: `TimeoutError: waiting for locator`
- UI element selector broke after a frontend deploy
- Use Locator Heal Agent to get alternatives:
  ```bash
  PYTHONPATH=. ./venv/bin/python3.11 cli.py debug \
    --test-file features/login/steps/web/login_web_app_test.py \
    --error "TimeoutError: waiting for locator '#email-input'"
  ```
- Request `data-testid` attribute from dev team

### DB connection refused
- VPN not connected
- DB host/port wrong in `.env`
- Check: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

## Severity classification (use for Jira bugs)

| Severity | Trigger |
|---------|---------|
| P0 | Blocks all users / data loss / crash |
| P1 | Smoke test fails / login / auth |
| P2 | Functional test fails — specific feature broken |
| P3 | Test code issue — app itself is fine |

## Root cause types

| Type | Meaning | Who fixes |
|------|---------|-----------|
| `product_bug` | App behaves incorrectly | Developer |
| `test_bug` | Test assertion or setup wrong | QE |
| `locator_issue` | UI selector broke | QE + dev (data-testid) |
| `environment_issue` | VPN / DB / CI infra | DevOps |
| `flaky_sync` | Timing issue in test | QE |

## Reporting a bug to Jira

```bash
# Debug agent can create Jira tickets directly
PYTHONPATH=. ./venv/bin/python3.11 -c "
from agents.debug_agent import FailureContext, debug_agent
ctx = FailureContext(
    test_name='test_TC_LOGIN_001_valid_user',
    error_message='AssertionError: expected 200 got 500',
    platform='api',
)
report = debug_agent.create_bug(ctx)
print(f'Jira: {report.jira_key}')
"
```
