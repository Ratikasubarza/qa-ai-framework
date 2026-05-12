# QA AI Framework Orchestration Spec

This spec defines how agents coordinate through LangGraph. Each node owns one
artifact boundary. Downstream nodes must reuse artifacts from state instead of
regenerating them.

## Shared State Artifacts

| Key | Owner | Purpose |
| --- | --- | --- |
| `requirements_output` | `requirements` | Full output from RequirementsAgent. |
| `acceptance_criteria` | `requirements` | Prompt-ready AC summaries. |
| `acceptance_criteria_details` | `requirements` | Full AC objects for traceability. |
| `testcase_output` | `testcase` | Full `TestCaseAgentOutput`; source of truth for approval and codegen. |
| `test_cases` | `testcase` | JSON-safe scenario list for reporting and coverage. |
| `approval` | `approval` | Decision metadata, reviewer, feedback, attempt. |
| `generated_files` | `codegen` | Dict of `{relative_path: absolute_path}`. |
| `execution_results` | `execute` | Pytest result metadata by absolute file path. |
| `failures` | `execute` | Normalized failure contexts for DebugAgent. |
| `bug_reports` | `debug` | Structured bug analysis for failed tests. |
| `coverage_report` | `skill_gap` | Coverage mapping, missing scenarios, saved report path. |

## Full QA Pipeline

```text
START
  -> requirements
  -> testcase
  -> approval
      -> codegen when approved
      -> report when rejected, timed out, or failed
  -> execute when files were generated
  -> debug when tests failed
  -> skill_gap
  -> report
END
```

## Node Contracts

### `requirements`

Input:
- `feature`
- `story_text` or `ticket_id`

Output:
- `requirements_output`
- `acceptance_criteria`
- `acceptance_criteria_details`

Rules:
- Jira and manual-story flows must both expose `criteria` and
  `acceptance_criteria`.
- Ticket drafts are derived artifacts and must not replace AC objects.

### `testcase`

Input:
- `feature`
- `story_text`
- `platforms`
- `acceptance_criteria`

Output:
- `testcase_output`
- `test_cases`

Rules:
- Approval is disabled inside `TestCaseAgent` for orchestrated runs.
- The full `TestCaseAgentOutput` is stored in state for codegen.

### `approval`

Input:
- `testcase_output`
- `test_cases`

Output:
- `approved`
- `approval`

Rules:
- This is the only approval gate in the LangGraph pipeline.
- If approval is disabled in settings, the node records `auto_approved`.
- Rejected, timed-out, or failed approvals route to `report`.

### `codegen`

Input:
- approved `testcase_output`
- `platforms`

Output:
- `generated_files`

Rules:
- Must never call `TestCaseAgent.run()`.
- Must generate code from the approved `testcase_output`.

### `execute`

Input:
- `generated_files.values()`

Output:
- `execution_results`
- `failures`

Rules:
- Must run with `./venv/bin/python3.11`.
- Missing generated files are normalized as failures.

### `debug`

Input:
- `failures`

Output:
- `bug_reports`

Rules:
- Runs only when failures exist.
- Jira creation remains a separate explicit action.

### `skill_gap`

Input:
- `acceptance_criteria`
- approved `test_cases`

Output:
- `coverage_report`
- `coverage_gaps`
- `coverage_percentage`
- `gap_report_path`

Rules:
- Coverage is measured against approved test cases, not regenerated cases.

### `report`

Input:
- full state

Output:
- `notifications`

Rules:
- Reports final state, failures, coverage, and approval/codegen errors.
- Telegram send failure must not fail the pipeline.

## Standalone Workflows

### Test Case Generation

Used by `cli.py generate testcase`.

```text
input -> TestCaseAgent -> optional internal approval -> printable/exportable output
```

This mode may still use `TestCaseAgent` approval for convenience. The
orchestrated pipeline passes `require_approval=False` and uses the graph gate.

### Requirements Drafting

```text
story/Jira -> RequirementsAgent -> AC objects -> QA ticket drafts
```

The AC objects remain the source of truth. Draft tickets are export artifacts.

### Reviewer Audit

```text
PRD + existing test cases -> ReviewerAgent -> traceability report -> Excel/CSV
```

Reviewer output is independent unless explicitly added as a quality gate.

### Locator Self-Healing

```text
locator failure -> DOM/screenshot snapshot -> LocatorAgent candidates
  -> candidate smoke test -> locator store/file update -> ops notification
```

The applied locator and snapshot id are the recovery artifacts.
