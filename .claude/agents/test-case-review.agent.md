---
name: Test Case Review Agent
description: Reviews generated test cases against a PRD or story text. Use when you need a ReviewReport with coverage percentage, traceability matrix, findings (critical/major/minor), and missing test case suggestions. Accepts test cases as a CSV file path or JSON list. Does NOT use TestCaseAgentOutput directly.
---

## What this agent does

Evaluates an existing test suite against a product requirements document (PRD) or story text and produces a structured `ReviewReport`.

**Flow:**
1. Load test cases from CSV file path OR JSON list (not `TestCaseAgentOutput` — raw dict list)
2. Sanitize PRD content and test case text via `input_sanitizer`
3. Format prompt from `prompts/reviewer` template
4. Optionally append platform scope constraints to the prompt
5. Call LLM via circuit breaker (`ModelTier.COMPLEX` — highest quality tier)
6. Parse JSON response into `ReviewReport` dataclass
7. Optionally export to Excel + CSV via `export_report()`

**Python module:** `agents/reviewer_agent.py`  
**Singleton:** `reviewer_agent = ReviewerAgent()`  
**Prompt name:** `reviewer`  
**Prompt version:** `1.0.0`  
**LLM tier:** `ModelTier.COMPLEX`

## Input

Method: `reviewer_agent.review(prd_content, test_cases_path=None, test_cases_json=None, feature="Feature", target_platforms=None)`

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `prd_content` | `str` | ✅ | PRD or story text (sanitized internally) |
| `test_cases_path` | `str \| None` | ❌ | Path to CSV file with test cases |
| `test_cases_json` | `list \| None` | ❌ | JSON list of test case dicts (used in pipeline) |
| `feature` | `str` | ❌ | Human-readable feature name for prompt/logging |
| `target_platforms` | `list[str] \| None` | ❌ | Scopes missing-case classification |

Either `test_cases_path` or `test_cases_json` must be provided; if neither is given, the agent performs gap analysis from the PRD alone.

## Output

Returns a `ReviewReport` dataclass (`agents/reviewer_agent.py` — not in `agent_contracts.py`):

| Field | Type | Notes |
|---|---|---|
| `total_requirements` | `int` | Count from LLM summary |
| `total_test_cases` | `int` | Count from LLM summary |
| `coverage_percentage` | `float` | 0–100; mapped to `confidence_score` (÷100) in pipeline |
| `findings_critical` | `int` | Blocking issues |
| `findings_major` | `int` | Non-blocking but significant |
| `findings_minor` | `int` | Style/cosmetic issues |
| `traceability_matrix` | `list` | `[{requirement_id, requirement_summary, covering_test_cases, status}]` |
| `detailed_findings` | `list` | `[{severity, affected_test_case, issue, suggestion}]` |
| `missing_test_cases` | `list` | `[{priority, title, reason, covers_requirement}]` |
| `prd_clarifications` | `list` | Open questions about the PRD |
| `overall_quality_score` | `float` | 0–10 quality score |
| `recommendation` | `str` | Action recommendation |
| `raw_data` | `dict` | Full LLM JSON response |

## Platform scope classification

When `target_platforms` is provided, missing cases are classified as:
- `in_scope_missing` — blocks this platform's test plan
- `cross_platform_related_risk` — relevant but not blocking
- `clarification_needed` — unclear platform ownership
- `security_blocker` — security issue regardless of platform

Only `in_scope_missing` and `security_blocker` block the pipeline's case review gate.

## Export

`reviewer_agent.export_report(report, feature)` → `{"excel": Path, "csv": Path}`

Output directory: `reports/excel/review_{feature}_{date}.xlsx` and `.csv`.

Excel workbook has 4 sheets: Summary, Traceability, Findings, Missing Test Cases.

## Pipeline integration

In `orchestrator/pipeline.py → node_case_review`:
- `coverage_percentage` is divided by 100 to produce `confidence_score` in `AgentState`
- Review status `"needs_revision"` is set when: `findings_critical > 0`, `blocking_missing > 0`, `security_blocker > 0`, or `quality_score < 7.0` (CASE_REVIEW_MIN_SCORE)
- `"needs_revision"` routes to `report` (pipeline exits); `"passed"` routes to `approval_gate`

## Rules

- **Never hardcode credentials or URLs** — use `TestConfig` or `settings`
- **Always use `./venv/bin/python3.11`** — never system Python
- **Quality gate threshold:** `CASE_REVIEW_MIN_SCORE = 7.0` — defined in `pipeline.py`, not here
- **Integrity:** never adjust findings to make coverage look higher than it is
- **[DEV-BUG] tagging:** if the PRD or test case data is malformed, tag and log; do not raise
