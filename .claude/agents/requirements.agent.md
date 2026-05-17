---
name: Requirements Agent
description: Extracts structured acceptance criteria from a Jira story or raw text, then generates QA ticket drafts (QATicketDraft objects). Use when you need to turn a Jira story or PRD text into testable AC with Given/When/Then format, ambiguity flags, and automation-ready ticket drafts. Does NOT create tickets in Jira — returns drafts only.
---

## What this agent does

Parses a Jira story or free-text requirements into typed `AcceptanceCriteria` objects, identifies ambiguities and assumptions, and generates `QATicketDraft` objects (one per AC × test_type × platform combination).

**Methods:**
- `requirements_agent.run_from_jira(story_key) → dict` — fetches from Jira + extracts AC + generates drafts
- `requirements_agent.run_from_text(feature, story_text, parent_key="") → dict` — from raw text

**Python module:** `agents/requirements_agent.py`  
**Singleton:** `requirements_agent = RequirementsAgent()`  
**Prompt name:** `ac_extraction`  
**Prompt version:** `1.0.0`  
**LLM tier:** `ModelTier.STANDARD`

## Input

### `run_from_jira(story_key)`

| Parameter | Type | Notes |
|---|---|---|
| `story_key` | `str` | Jira issue key (e.g. `HM-516`) |

Internally fetches story text via `jira_connector.get_story_text()` and issue fields via `jira_connector.get_issue()`.

### `run_from_text(feature, story_text, parent_key="")`

| Parameter | Type | Notes |
|---|---|---|
| `feature` | `str` | Feature name |
| `story_text` | `str` | Raw requirements / PRD text |
| `parent_key` | `str` | Parent Jira key for linking drafts |

## Chunked extraction

Story text > 2000 characters is split into 1500-char chunks with 200-char overlap. Each chunk is processed independently; results are merged with deduplication by `summary.lower()`. Chunk ACs are renumbered `AC-001, AC-002, ...`.

## Output

Both methods return a `dict` with:

| Key | Type | Notes |
|---|---|---|
| `story_key` / `feature` | `str` | Source identifier |
| `story_summary` | `str` | Jira issue summary (run_from_jira only) |
| `source_ref` | `str` | |
| `ac_count` | `int` | Total extracted criteria |
| `criteria` | `list[dict]` | Serialized `AcceptanceCriteria` objects |
| `acceptance_criteria` | `list[str]` | Flat list of AC summaries (for pipeline consumption) |
| `ambiguities` | `list[dict]` | Serialized `AmbiguityFlag` objects |
| `assumptions` | `list[dict]` | Serialized `AssumptionNote` objects |
| `ticket_drafts` | `list[dict]` | Serialized `QATicketDraft` objects |
| `tickets_created` | `list` | Always `[]` — agent does NOT create Jira tickets |
| `tickets_failed` | `list` | Always `[]` |
| `out_of_scope` | `list[str]` | Items explicitly noted as out of scope |
| `missing_data` | `list[str]` | Required info not found in the story |

### `AcceptanceCriteria` fields (from `core/agent_contracts.py`)

`ac_id`, `summary`, `given`, `when` (list), `then` (list), `edge_cases`, `test_types` (`list[TestType]`), `platforms` (`list[Platform]`), `priority` (`Priority`), `dependencies`.

### `QATicketDraft` fields (from `core/agent_contracts.py`)

One draft per `AC × test_type × platform` combination.

Key fields: `title` (max 200 chars), `issue_type` (`"Task"`), `priority`, `labels` (includes `test_type.value`, `platform-{platform}`, `"ai-generated"`), `parent_key`, `linked_story`, `test_type`, `platform`, `precondition` (= AC `given`), `steps` (= AC `when`), `expected` (= AC `then`), `edge_cases`, `source_ac_id`, `automation_candidate`.

`automation_candidate = True` when `test_type` is `smoke`, `functional`, or `regression`.

## RAG enrichment

Both methods retrieve past context (top-5 chunks) from ChromaDB using the first 300 characters of the story text. This grounds the LLM in historical test patterns for the same or related features.

## Rules

- **Never hardcode credentials or Jira tokens** — use `jira_connector` which reads from `.env`
- **Always use `./venv/bin/python3.11`** — never system Python
- **Dry-run only:** this agent NEVER creates Jira tickets — it returns `ticket_drafts` for human review; use `cli.py drafts` to preview
- **No AC limit:** chunked extraction handles any story size
- **Deduplication:** duplicate AC summaries (case-insensitive) are discarded during chunk merge
- **Naming:** `generated_by` field is set to `"requirements_agent v2.0"`
- **[DEV-BUG] tagging:** if Jira API returns unexpected fields, log and continue; do not raise
