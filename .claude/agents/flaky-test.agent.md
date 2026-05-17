---
name: Flaky Test Agent
description: Identifies intermittently failing tests from their run history. Use when you have a list of test outcomes (PASS/FAIL sequences) and want to classify each test's flakiness cause and get a remediation recommendation. Returns None for stable tests; never quarantines genuine product bugs.
---

## What this agent does

Computes a flakiness score from a test's pass/fail history, then calls an LLM to classify the root cause and suggest remediation.

**Methods:**
- `flaky_test_agent.analyze(test_name, outcomes, errors) → FlakyTestResult | None` — single test
- `flaky_test_agent.analyze_batch(test_history, flakiness_threshold=0.20) → list[FlakyTestResult]` — multiple tests, sorted by score descending

**Returns `None`** for stable tests: always-pass, always-fail, or fewer than 3 total runs.

**Python module:** `agents/flaky_test_agent.py`  
**Singleton:** `flaky_test_agent = FlakyTestAgent()`  
**LLM tier:** `ModelTier.FAST`  
**Prompt:** Inline `ANALYSIS_PROMPT` constant

## Input

### `analyze(test_name, outcomes, errors)`

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `test_name` | `str` | ✅ | Test identifier (sanitized before LLM) |
| `outcomes` | `list[str]` | ✅ | Ordered oldest→newest; values must be `"PASS"` or `"FAIL"` |
| `errors` | `list[str] \| None` | ❌ | Error messages for FAIL runs; deduplicated to top-5 unique patterns |

### `analyze_batch(test_history, flakiness_threshold=0.20)`

`test_history` is a list of dicts, each containing:

| Key | Type | Notes |
|---|---|---|
| `test_name` | `str` | Test name |
| `outcomes` | `list[str]` | `"PASS"` or `"FAIL"` entries |
| `errors` | `list[str]` | Error messages for failed runs |

Only tests with `flakiness_score >= flakiness_threshold` are returned.

## Flakiness score algorithm

**Alternation rate:** count how many consecutive outcome pairs differ.

```
score = transitions / (total_runs - 1)
```

- `1.0` = every run flips (PASS/FAIL/PASS/FAIL)
- `0.0` = always same result (stable, not returned)

## Output

`FlakyTestResult` dataclass:

| Field | Type | Notes |
|---|---|---|
| `test_name` | `str` | |
| `flakiness_score` | `float` | 0.0–1.0, rounded to 3 decimal places |
| `failure_count` | `int` | |
| `total_runs` | `int` | |
| `category` | `str` | One of 7 categories (see below) |
| `confidence` | `str` | `"high" \| "medium" \| "low"` |
| `root_cause` | `str` | Specific explanation from LLM |
| `remediation` | `str` | Exact fix to apply |
| `quarantine_recommended` | `bool` | Always `False` when `category == "genuine_bug"` |
| `error_patterns` | `list[str]` | Deduplicated error messages (max 5) |

## Flakiness categories

| Category | Meaning |
|---|---|
| `timing` | Race condition, async not awaited, sleep too short |
| `data_dependency` | Shared/leftover state from another test |
| `external_service` | Network, API rate limit, third-party instability |
| `locator` | UI element locator brittle or timing-dependent |
| `environment` | CI vs local discrepancy, resource contention |
| `test_order` | Test assumes a previous test ran first |
| `genuine_bug` | Real product instability causes intermittent failure |

## Quarantine safety lock

The agent programmatically enforces:
```python
if category == "genuine_bug":
    quarantine_recommended = False
```

This prevents the LLM from recommending quarantine for a test that is correctly detecting a real product defect.

## Rules

- **Integrity first:** `genuine_bug` category → remediation must describe the developer-side fix, never suggest suppressing the test
- **Low confidence → `genuine_bug`:** if the LLM cannot determine the cause, it must classify as `genuine_bug` and treat it as product instability
- **Do not invent root causes** — only state what the error patterns directly support
- **Never hardcode credentials or URLs** — use `TestConfig` or `settings`
- **Always use `./venv/bin/python3.11`** — never system Python
- **Minimum history:** returns `None` for tests with < 3 runs — insufficient data
