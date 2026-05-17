---
name: Test Case Generation Agent
description: Generates structured QA test cases from a feature description, acceptance criteria, Jira story, and/or Confluence PRD. Use when you need to produce a TestCaseAgentOutput with validated ScenarioSchema objects. Supports automatic AC chunking (>8 criteria), RAG context injection, Jira enrichment, and optional Telegram approval.
---

## What this agent does

Converts a feature specification into typed, validated test scenarios (`TestCaseAgentOutput`).

**Flow:**
1. Sanitize all inputs via `input_sanitizer`
2. Enrich from Jira story (`jira_story_key`) — fetches description, existing QA subtasks to avoid duplication, merges AC if caller did not supply any
3. Enrich from Confluence PRD (`confluence_page_url`) — fetches page text and appends as context
4. Retrieve past context from ChromaDB RAG (top-5 relevant chunks)
5. AC > 8 → split into batches of 8, call LLM per batch, merge results (`_run_chunked_generation`)
6. AC ≤ 8 → single LLM call (`_run_single_generation`)
7. Parse LLM response with JSON salvage for truncated outputs
8. Optionally send to Telegram for QA Lead approval (`require_approval=True`)

**Python module:** `agents/test_case_agent.py`  
**Singleton:** `test_case_agent = TestCaseAgent()`  
**Prompt name:** `test_case_gen`  
**Prompt version:** `2.0.0`  
**LLM tier:** `ModelTier.STANDARD`

## Input

Accepts a `TestCaseAgentInput` Pydantic model (`core/agent_contracts.py`):

| Field | Type | Required | Notes |
|---|---|---|---|
| `feature` | `str` | ✅ | Human-readable feature name |
| `description` | `str` | ✅ | Raw feature description or story text |
| `platforms` | `list[Platform]` | ✅ | e.g. `[Platform.WEB, Platform.API]` |
| `acceptance_criteria` | `list[str]` | ❌ | Merged from Jira if empty and `jira_story_key` set |
| `jira_story_key` | `str \| None` | ❌ | Fetches issue, subtasks, and AC from Jira |
| `confluence_page_url` | `str \| None` | ❌ | Fetches Confluence PRD page text |
| `context` | `str \| None` | ❌ | Extra free-form context prepended to RAG output |

`require_approval` (`bool | None`) is a separate `run()` parameter — defaults to `settings.approval_required`. Set `False` in `node_testcase` because the pipeline owns the approval gate.

## Output

Returns `TestCaseAgentOutput` (`core/agent_contracts.py`):

| Field | Type | Notes |
|---|---|---|
| `feature` | `str` | Passed through from input |
| `scenarios` | `list[ScenarioSchema]` | Fully typed scenario objects |
| `coverage_summary` | `str` | LLM-generated or batch-merge summary |
| `total_scenarios` | `int` | `len(scenarios)` |
| `prompt_version` | `str` | Always `"2.0.0"` |
| `model_used` | `str` | Model ID from LLM response (comma-joined for batch) |
| `generated_at` | `datetime` | UTC timestamp |
| `tokens_used` | `int` | Cumulative across all batches |
| `confidence_score` | `float` | `0.0` default; set by `node_case_review` in pipeline (coverage/100) |

Each `ScenarioSchema` contains: `scenario_id` (TC-NNN), `name`, `precondition`, `steps` (`list[TestStep]`), `expected_result`, `test_data`, `tags`, `test_type` (`TestType`), `platforms` (`list[Platform]`), `priority` (`Priority`), `edge_cases`, `combination_edge_cases`, `weird_edge_cases`, `regression_candidate`, `regression_risk_area`.

## Priority mapping

| LLM value | `Priority` enum |
|---|---|
| `P0` / `HIGH` | `Priority.HIGH` |
| `P1` / `MEDIUM` | `Priority.MEDIUM` |
| `P2` / `LOW` | `Priority.LOW` |

## Platform normalization

`mobile` → first platform in input list (or `android`). `flutter_android` → `flutter-android`. Values not in the `Platform` enum are silently dropped; defaults to input platforms.

## Rules

- **Never hardcode credentials or URLs** — use `TestConfig` or `settings`
- **Always use `./venv/bin/python3.11`** — never system Python
- **Naming:** `scenario_id` uses `TC-NNN` format
- **Chunking threshold:** `MAX_AC_PER_BATCH = 8` — do not lower without updating batch prompt
- **JSON salvage:** truncated JSON attempts partial recovery; `coverage_summary` will note `"json_truncated"` when this occurs
- **Jira deduplication:** existing QA subtasks are injected as context to avoid regenerating already-created test cases
- **Integrity:** never weaken assertions, never skip edge cases to increase pass rate
- **[DEV-BUG] tagging:** if Jira/Confluence API returns unexpected data, tag with `[DEV-BUG]` and continue gracefully
