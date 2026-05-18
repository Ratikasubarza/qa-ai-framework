# How to Run Tests

## Prerequisites

- Python 3.11 venv installed at `./venv/`
- `.env` file configured (copy from `.env.example`)
- VPN connected for DB access (staging MySQL)

## Run all API tests

```bash
PYTHONPATH=. ./venv/bin/python3.11 -m pytest \
  features/login/steps/api/ \
  features/register/steps/api/ \
  features/cms_login/steps/api/ \
  features/cms_users/steps/api/ \
  features/onboarding/steps/api/ \
  -v --tb=short
```

## Run a single feature

```bash
PYTHONPATH=. ./venv/bin/python3.11 -m pytest \
  features/login/steps/api/login_api_test.py -v --tb=short
```

## Run by marker

```bash
# Smoke tests only (P0 — fastest gate)
PYTHONPATH=. ./venv/bin/python3.11 -m pytest -m smoke -v

# Regression suite
PYTHONPATH=. ./venv/bin/python3.11 -m pytest -m regression -v

# API tests only
PYTHONPATH=. ./venv/bin/python3.11 -m pytest -m api -v

# Negative tests only
PYTHONPATH=. ./venv/bin/python3.11 -m pytest -m negative -v
```

## Run with timeout (recommended for CI)

```bash
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/ \
  --timeout=30 --tb=short -v
```

## Run web tests (Playwright)

```bash
PYTHONPATH=. ./venv/bin/python3.11 -m pytest \
  features/login/steps/web/ -v --tb=short
```

## Generate JUnit XML (for CI)

```bash
PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/ \
  --junit-xml=reports/junit/results.xml -v --tb=short
```

## Verify syntax before running

```bash
PYTHONPATH=. ./venv/bin/python3.11 -m py_compile features/login/steps/api/login_api_test.py
./venv/bin/python3.11 -m ruff check . --select E,W,F --ignore E501,E402
```

## Common failure causes

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `AssertionError: expected 200 got 401` | Staging creds missing or expired | Check `STAGING_EMAIL`/`STAGING_PASSWORD` in `.env` |
| `ConnectionRefusedError` | VPN not connected | Connect VPN before running DB-dependent tests |
| `Email sending quota reached` | Resend daily limit hit | Wait until midnight SGT or use existing approved user |
| `Token not found in response` | CMS credentials wrong | Check `CMS_EMAIL`/`CMS_PASSWORD` in `.env` |
| `ModuleNotFoundError` | PYTHONPATH missing | Prefix with `PYTHONPATH=.` |
