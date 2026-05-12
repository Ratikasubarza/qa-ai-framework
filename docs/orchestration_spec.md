# QA AI Framework Orchestration Spec

This spec defines how agents coordinate through LangGraph. Each node owns one
artifact boundary. Downstream nodes must reuse artifacts from state instead of
regenerating them.

## Architecture Position

The framework is a QA orchestration system, not a collection of standalone
agents. The orchestrator owns flow control, approval gates, retries, reporting,
and artifact lineage. Agents own specialist work only.

Recommended layers:

| Layer | Responsibility | Examples |
| --- | --- | --- |
| Entry points | User/CI commands and inputs | `cli.py pipeline`, Jira ticket, story text |
| Orchestrator | Flow, state, routing, gates | `orchestrator/pipeline.py` |
| Agents | Specialist reasoning/generation | Requirements, TestCase, CodeGen, Debug, SkillGap |
| Skills/adapters | File/export/platform integrations | Excel writer, Jira, Telegram, Playwright, Appium |
| State/artifacts | Traceable outputs between nodes | AC, approved tests, exports, generated files, reports |

Hard rule: agents do not call each other to recreate upstream artifacts inside
the full pipeline. They receive approved state from the orchestrator.

## Team Operating Model

| Role | Owns | Uses |
| --- | --- | --- |
| Product Owner | Story clarity, acceptance criteria | `requirements_output`, ambiguity questions |
| QA Lead | Test strategy approval | Telegram approval, CSV/Excel exports |
| QA Engineer | Manual and exploratory validation | Approved Excel/CSV, coverage gaps |
| Automation Engineer | Generated test code review and maintenance | `generated_files`, pytest reports |
| Developer | Product bug fixes and testability hooks | bug reports, locator/self-heal recommendations |
| AI/Framework Engineer | Agent quality, prompts, orchestration contracts | evals, pipeline tests, prompt registry |

The pipeline should produce artifacts the whole feature team can read:

```text
PO: ambiguities and assumptions
QA Lead: approved test case plan
QA Engineer: CSV/Excel test execution artifact
Automation Engineer: generated pytest/Appium/API tests
Developer: debug report and reproducible failure context
AI Engineer: prompt/model/version lineage and coverage metrics
```

## Shared State Artifacts

| Key | Owner | Purpose |
| --- | --- | --- |
| `requirements_output` | `requirements` | Full output from RequirementsAgent. |
| `acceptance_criteria` | `requirements` | Prompt-ready AC summaries. |
| `acceptance_criteria_details` | `requirements` | Full AC objects for traceability. |
| `testcase_output` | `testcase` | Full `TestCaseAgentOutput`; source of truth for approval, export, and codegen. |
| `test_cases` | `testcase` | JSON-safe scenario list for reporting and coverage. |
| `approval` | `approval` | Decision metadata, reviewer, feedback, attempt. |
| `testcase_exports` | `testcase_export` | Approved CSV/Excel test case artifact paths. |
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
      -> testcase_export when approved
      -> report when rejected, timed out, or failed
  -> codegen when exports were created
  -> execute when files were generated
  -> debug when tests failed
  -> skill_gap
  -> report
END
```

## Feature Team Workflow

Use this as the concrete end-to-end process for a product feature.

### 1. Intake

Trigger:
- Jira story key, or
- raw story text from CLI/local development.

Required input:
- feature name
- target platforms: `web`, `api`, `android`, `ios`, or combinations
- story/acceptance criteria source

Definition of Ready:
- story has a business goal
- expected behavior is testable
- target platform is known
- required test data is either provided or explicitly marked missing

Output:
- `requirements_output`
- `acceptance_criteria`
- ambiguity and assumption list

### 2. Test Design

The TestCaseAgent creates scenarios from accepted AC. It should cover:
- positive flows
- negative flows
- boundary cases
- platform-specific behavior
- important regression paths

Output:
- `testcase_output`
- `test_cases`

Rule:
- this is draft until the approval node marks it approved.

### 3. QA Lead Approval

QA Lead reviews the generated scenarios before they become official.

Approval decisions:
- approve: continue to export and automation generation
- reject: stop and report feedback
- edit: treat as not approved until an edit workflow exists
- timeout: stop in CI; local auto-approval is allowed only when configured

Output:
- `approval`
- `approved`

### 4. Official Test Plan Export

The pipeline exports only approved test cases.

Output:
- CSV for lightweight sharing/import
- Excel for QA review and manual execution

Artifact owner:
- `testcase_export`

Rule:
- if export fails, the pipeline stops before codegen because the team does not
  have an official test plan artifact.

### 5. Automation Generation

CodeGen consumes the same approved `testcase_output` used for CSV/Excel.

Output:
- `generated_files`

Rules:
- do not regenerate test cases
- do not hardcode credentials
- use `TestConfig`/test data classes for environment data

### 6. Execution

Run generated/affected tests with the project venv.

Command standard:

```bash
PYTHONPATH=. ./venv/bin/python3.11 -m pytest [test_file] -v --tb=short
```

Output:
- `execution_results`
- `failures`
- pytest JSON report

### 7. Failure Analysis

DebugAgent runs only when execution fails.

Output:
- `bug_reports`

Rules:
- classify failures as product bug, test code issue, environment issue, or data
  issue
- Jira bug creation should remain explicit, not hidden inside analysis

### 8. Coverage Analysis

SkillGap compares approved test cases against AC.

Output:
- `coverage_report`
- `gap_report_path`

Definition of Done:
- approved test plan exists
- CSV/Excel export exists
- generated automation exists or a reason is recorded
- execution result exists
- coverage report exists
- unresolved gaps are visible to the team

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

### `testcase_export`

Input:
- approved `testcase_output`

Output:
- `testcase_exports`

Rules:
- Exports only approved test cases.
- CSV and Excel must come from the same `testcase_output` consumed by codegen.
- Export failure routes to `report` instead of continuing with missing official
  artifacts.

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

## CI/CD Recommendation

Use three pipeline tiers so the team does not wait on expensive workflows for
every small change.

| Tier | Trigger | Runs | Blocks Merge |
| --- | --- | --- | --- |
| Fast | every PR | unit tests, lint/import checks, orchestration contract tests | yes |
| Feature | QA label or story-ready branch | pipeline through export/codegen, targeted tests | yes for QA-owned branches |
| Nightly | scheduled | full generated suites, debug analysis, skill gap reports | no, but opens follow-up work |

Minimum PR gate:

```bash
PYTHONPATH=. ./venv/bin/python3.11 -m pytest tests/test_pipeline_orchestration.py -v --tb=short
./venv/bin/python3.11 -m ruff check . --select E,W,F --ignore E501,E402
```

## Artifact Naming

Recommended naming conventions:

| Artifact | Pattern |
| --- | --- |
| Pipeline run id | `YYYYMMDD_HHMMSS` |
| Test plan CSV | `reports/excel/test_plan_<feature>_<YYYYMMDD>.csv` |
| Test plan Excel | `reports/excel/test_plan_<feature>_<YYYYMMDD>.xlsx` |
| Pytest report | `reports/pytest_<test_file_stem>.json` |
| Gap report | `reports/gap_reports/<feature>_<run_id>.json` |

For future improvement, include `run_id` in CSV/Excel filenames to avoid
overwriting multiple approved runs on the same day.

## Architecture Review Notes

Current strengths:
- approved `testcase_output` is reused by export and codegen
- CSV/Excel export is a separate graph node
- execution uses the project Python runtime
- downstream nodes no longer regenerate upstream artifacts
- orchestration contract tests cover the riskiest handoffs

Recommended next improvements:
- add retry/edit workflow for rejected approvals instead of stopping at report
- add a reviewer quality gate before human approval for large stories
- add `run_id` to exported CSV/Excel filenames
- persist full pipeline state as JSON for audit/debug replay
- split web/API/mobile codegen by platform instead of using only `platforms[0]`
- add CI mode that disables Telegram and uses deterministic approval policy
