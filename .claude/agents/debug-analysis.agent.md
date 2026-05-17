---
name: Debug Analysis Agent
description: Analyzes test failures and optionally creates Jira bug tickets. Use when a test has failed and you need root cause classification, severity (P0–P3), and a structured bug report. Call analyze() for report only, create_bug() to also open a Jira ticket and send Telegram notification.
---

## What this agent does

Receives a `FailureContext` (test name, error message, stack trace, platform) and produces a `BugReport` with root cause, severity classification, and remediation guidance.

**Methods:**
- `debug_agent.analyze(failure: FailureContext) → BugReport` — LLM analysis only, no Jira
- `debug_agent.create_bug(failure, parent_story=None) → BugReport` — analyze + Jira ticket + Telegram notify
- `debug_agent.analyze_from_pytest(test_name, longrepr, platform, screenshot) → BugReport` — convenience wrapper for pytest failure hooks

**Python module:** `agents/debug_agent.py`  
**Singleton:** `debug_agent = DebugAgent()`  
**LLM tier:** `ModelTier.STANDARD`  
**Prompt:** Inline `ANALYSIS_PROMPT` constant (not from `prompt_manager`)

## Input

`FailureContext` dataclass:

| Field | Type | Required | Notes |
|---|---|---|---|
| `test_name` | `str` | ✅ | Name of the failed test |
| `error_message` | `str` | ✅ | Error text (sanitized before LLM) |
| `platform` | `str` | ❌ | Default `"web"` |
| `location` | `str` | ❌ | URL or screen name where failure occurred |
| `stack_trace` | `str` | ❌ | Full stack trace (truncated to 2000 chars before LLM) |
| `screenshot` | `str \| None` | ❌ | Screenshot path/URL (included in Jira description) |
| `logs` | `list[str]` | ❌ | Last 20 log lines appended as context |
| `extra_context` | `dict` | ❌ | Additional key-value context |

## Output

`BugReport` dataclass:

| Field | Type | Notes |
|---|---|---|
| `root_cause` | `str` | Specific cause identified by LLM |
| `bug_type` | `str` | `ui_bug \| api_bug \| test_code \| environment \| regression` |
| `failure_classification` | `str` | `product_bug \| developer_bug \| test_bug \| locator_issue \| test_data_issue \| environment_issue \| flaky_sync \| unknown` |
| `confidence` | `float` | 0.0–1.0 LLM confidence |
| `recommended_action` | `str` | `create_bug_report \| fix_test_code \| update_locator \| fix_test_data \| report_environment_issue \| ask_human_triage` |
| `auto_fix_allowed` | `bool` | Only `True` when classification is `test_bug / locator_issue / flaky_sync` AND confidence ≥ 0.8 |
| `integrity_notes` | `list[str]` | Why this failure should not be hidden |
| `severity` | `str` | `P0 \| P1 \| P2 \| P3` |
| `title` | `str` | Concise bug title, max 100 chars |
| `description` | `str` | Detailed description |
| `steps_to_reproduce` | `list[str]` | Numbered reproduction steps |
| `expected_behavior` | `str` | What should have happened |
| `actual_behavior` | `str` | What actually happened |
| `affected_component` | `str` | Module or UI component |
| `suggested_fix` | `str` | Optional fix if obvious |
| `needs_dev_attention` | `bool` | Whether a developer must act |
| `labels` | `list[str]` | Jira labels (default `["ai-detected", "qa-automation"]`) |
| `jira_key` | `str \| None` | Populated by `create_bug()` |
| `created_at` | `datetime` | Timestamp |

## Severity override rules (deterministic)

If the LLM returns no severity, the agent applies these fallback rules:
- Error contains `"all users"`, `"blocks all"`, `"crash"`, `"data loss"` → `P0`
- Test name contains `"smoke"`, `"login"`, `"auth"` → `P1`
- Otherwise → `P2`

## `auto_fix_allowed` safety lock

The agent programmatically enforces:
```
if classification not in {test_bug, locator_issue, flaky_sync}:
    auto_fix_allowed = False
if confidence < 0.8:
    auto_fix_allowed = False
```

This prevents the LLM from returning `auto_fix_allowed=True` for product bugs.

## CLI usage

```bash
PYTHONPATH=. ./venv/bin/python3.11 cli.py debug \
  --test-file features/login/steps/login_api_test.py \
  --error "AssertionError: expected 200 got 401" \
  --platform api
```

## Rules

- **Integrity first:** never suggest removing assertions, weakening expected values, or skipping tests to make a product bug disappear
- **Product/API bugs must preserve the failing signal** — only `test_code`, `locator_issue`, and `flaky_sync` classifications allow automation fixes
- **Never hardcode credentials or Jira tokens** — use `secret_manager` or `.env`
- **Always use `./venv/bin/python3.11`** — never system Python
- **`[DEV-BUG]` tagging:** if Jira ticket creation fails, log with `[DEV-BUG]` and return the `BugReport` without the `jira_key`
