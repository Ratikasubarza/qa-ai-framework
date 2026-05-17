---
name: Skill Gap Agent
description: Compares acceptance criteria against generated test cases to identify untested scenarios and calculate coverage percentage. Use after test case generation to find gaps in coverage. Also saves a JSON gap report to reports/gap_reports/. Part of the Phase 9 pipeline (node_skill_gap runs after node_debug).
---

## What this agent does

Takes a list of acceptance criteria strings and a list of test case dicts, maps each AC to covering test cases via LLM, then returns a gap analysis with coverage percentage and untested scenario recommendations.

**Python module:** `agents/skill_gap_agent.py`  
**Singleton:** `skill_gap_agent = SkillGapAgent()`  
**LLM tier:** `ModelTier.STANDARD`  
**Prompt:** Inline `SYSTEM_PROMPT` constant (not from `prompt_manager`)

## Input

Method: `skill_gap_agent.analyze(acceptance_criteria, test_cases, feature="")`

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `acceptance_criteria` | `list[str]` | ✅ | Plain-text AC summaries (e.g. from `node_requirements` output) |
| `test_cases` | `list[dict]` | ✅ | Test case dicts with `scenario_id` and `name`/`title` |
| `feature` | `str` | ❌ | Feature name for logging and report metadata |

## Output

Returns a `dict`:

| Key | Type | Notes |
|---|---|---|
| `coverage_percentage` | `float` | 0.0–100.0 |
| `covered_ac` | `list[str]` | AC IDs or summaries with test coverage |
| `uncovered_ac` | `list[str]` | AC IDs or summaries with NO test coverage |
| `missing_scenarios` | `list[str]` | Specific test scenarios recommended to add |
| `recommendations` | `list[str]` | General coverage improvement suggestions |

### Deterministic fallback

If the LLM call fails:
```python
coverage_percentage = len(test_cases) / max(len(acceptance_criteria), 1) * 100
covered_ac = []
uncovered_ac = acceptance_criteria   # all assumed uncovered
missing_scenarios = []
recommendations = ["Review test cases manually — LLM analysis failed"]
```

## Report persistence

Method: `skill_gap_agent.save_report(gap_data, feature, run_id) → str`

Saves the gap analysis as JSON to `reports/gap_reports/{feature}_{run_id}.json`.

Includes additional fields: `feature`, `run_id`, `timestamp` (ISO format).

Returns the absolute path string.

## Pipeline integration

In `orchestrator/pipeline.py → node_skill_gap`:
- Called after `node_debug` (or directly after `node_execute` if no failures)
- `coverage_percentage` is stored in `AgentState["coverage_percentage"]`
- `missing_scenarios` → `AgentState["coverage_gaps"]`
- `gap_report_path` → `AgentState["gap_report_path"]`
- The skill gap report path appears in the Telegram summary from `node_report`

## Rules

- **Never hardcode credentials or URLs** — use `TestConfig` or `settings`
- **Always use `./venv/bin/python3.11`** — never system Python
- **Integrity:** coverage percentage must reflect actual mapping, not be inflated — if the LLM cannot confirm coverage, mark AC as uncovered
- **Fallback is safe:** a failed LLM call returns a conservative estimate (0% covered) rather than false confidence
- **Test case format:** the agent reads `scenario_id` and `name`/`title` from dicts — ensure test cases are in standard dict form (from `_scenario_to_dict()` in pipeline) before calling
