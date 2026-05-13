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
| `source_bundle` | `source_intake` | Normalized Jira/PRD/URL/existing-test context. |
| `requirements_output` | `requirements` | Full output from RequirementsAgent. |
| `acceptance_criteria` | `requirements` | Prompt-ready AC summaries. |
| `acceptance_criteria_details` | `requirements` | Full AC objects for traceability. |
| `testcase_output` | `testcase` | Full `TestCaseAgentOutput`; source of truth for approval, export, and codegen. |
| `test_cases` | `testcase` | JSON-safe scenario list for reporting and coverage. |
| `case_review` | `case_review` | AI quality gate summary before QA Lead approval. |
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
  -> source_intake
  -> requirements
  -> testcase
  -> case_review
      -> approval when AI quality gate passes
      -> report when critical gaps or low quality score are found
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

## Golden Workflow Alignment

The attached Golden Workflows document describes a broader engineering workflow
around the QA pipeline. This framework should implement that guidance with local
Python adapters and existing project conventions, not by forcing credentialed
external links or MCP servers during local runs.

Target end-to-end operating model:

```text
Product source
  -> backlog refinement
  -> requirements extraction
  -> story coverage analysis
  -> test case generation
  -> AI case review
  -> QA Lead approval
  -> CSV/Excel official test plan
  -> optional TestRail import
  -> locator/page-object preparation
  -> automation codegen
  -> execution
  -> debug and coverage report
  -> post-deployment healing
```

Principles:
- read only sources the current user can access
- preserve credential boundaries; never force-open another person's Confluence,
  Jira, or private MCP resource
- keep every workflow artifact traceable to the original story, PRD, Jira issue,
  observed URL, or existing test case file
- make generated CSV/Excel the official handoff from QA design into automation
- separate human approval, AI review, code generation, and test execution gates

## Future Architecture Lanes

These lanes make the framework useful for more than one person and more than one
phase of delivery.

| Lane | Purpose | Recommended Nodes/Adapters | Status |
| --- | --- | --- | --- |
| Backlog refinement | Convert PRD/Jira context into implementation-ready work | `prd_sync`, `task_breakdown`, `story_coverage`, `jira_backfill` | Future |
| QA test design | Generate, review, approve, and export test cases | `source_intake`, `requirements`, `testcase`, `case_review`, `approval`, `testcase_export` | Implemented core |
| Automation generation | Turn approved test cases into maintainable tests | `locator_page_object`, `codegen`, `execute` | Partial |
| Failure triage | Classify failures and produce bug/debug reports | `debug`, `skill_gap`, `report` | Implemented core |
| Maintenance healing | Repair brittle UI automation safely after deployment | `healer_baseline`, `failure_analyzer`, `repair_decision`, `ui_trace_diagnoser`, `surrender` | Future |

The current graph should remain narrow and reliable. New lanes should be added
as explicit graph nodes or standalone commands only when their artifact contract
is clear.

## Feature Team Workflow

Use this as the concrete end-to-end process for a product feature.

### 1. Intake

Trigger:
- Jira story key, or
- raw story text from CLI/local development.
- optional implemented feature URL.
- optional existing CSV/manual test cases.

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
- `source_bundle`
- source references
- intake quality flags

Optional source types:
- Confluence/PRD text pasted by the user
- Confluence PRD URL via `--prd-url`
- Jira ticket text or key when the current user has access
- Jira subtasks/developer implementation notes via `--include-subtasks`
- implemented feature URL
- existing CSV/Excel/manual test cases
- screenshots or observed behavior notes

If a source requires unavailable credentials, the pipeline records it as
`not_accessible` and continues with the sources that were provided.

Recommended scope rule:
- Use Jira story/ticket as the execution scope for generation.
- Use Confluence PRD as parent product context, not as the only source for a
  broad end-to-end test plan.
- Use subtasks when the ticket has API, mobile, or implementation details that
  are more precise than the PRD.
- Prefer one focused run per Jira story/substory for maintainable TDD output.

When `--include-subtasks` is used, source intake filters subtasks by platform:
- `api` prioritizes `[BE]`, API, endpoint, contract, payload, and schema tasks.
- `android` and `ios` prioritize `[Mobile]`, mobile, Appium, and Flutter tasks.
- `web` prioritizes `[FE]`, frontend, web, CMS, browser, and Playwright tasks.
- if no platform-specific subtask is detected, all subtasks are retained as a
  fallback so unlabeled teams do not lose context.

Preferred Jira + PRD command:

```bash
PYTHONPATH=. ./venv/bin/python3.11 cli.py pipeline \
  --feature "Post Composer API" \
  --platform api \
  --ticket "HM-123" \
  --prd-url "https://thehono.atlassian.net/wiki/spaces/H/pages/37847042/PRD+-+Sprint+3+-+Post+Management" \
  --include-subtasks
```

Preferred Confluence PRD command:

```bash
PYTHONPATH=. ./venv/bin/python3.11 cli.py pipeline \
  --feature "Sprint 3 - Post Management" \
  --platform android \
  --prd-url "https://thehono.atlassian.net/wiki/spaces/H/pages/37847042/PRD+-+Sprint+3+-+Post+Management"
```

### 1.5 Backlog Refinement and Story Coverage

This phase is recommended before QA automation for larger features.

Workflow:

```text
PRD/Jira source
  -> sync product context
  -> break down implementation tasks
  -> map story coverage
  -> identify missing acceptance criteria
  -> optionally update Jira task description
```

Outputs:
- refined requirement list
- implementation task breakdown
- story coverage gaps
- clarification questions for PO/PM

Rule:
- backlog refinement does not generate automation code. It improves the source
  material that later feeds requirements and test design.

### 2. Requirements Extraction

RequirementsAgent extracts AC from the source bundle.

Output:
- `requirements_output`
- `acceptance_criteria`
- ambiguity and assumption list

### 3. Test Design

The TestCaseAgent creates scenarios from accepted AC. It should cover:
- positive flows
- negative flows
- boundary cases
- platform-specific behavior
- important regression paths
- permission and role-based behavior when mentioned
- API contract behavior when platform includes `api`
- security-sensitive inputs when the PRD exposes auth, input, or permission risk

Output:
- `testcase_output`
- `test_cases`

Rule:
- this is draft until the approval node marks it approved.
- priority should follow team convention: `P0` for release-blocking/high-risk,
  `P1` for important standard coverage, and `P2` for lower-risk or extended
  coverage.
- generated cases must be traceable to requirement IDs or AC summaries.
- new-feature requirement coverage should default to `functional`, not
  `regression`.
- `regression` is reserved for existing behavior that may be impacted by the
  new feature and must include a concrete regression risk area.
- large PRDs must be generated in AC batches so each LLM response stays valid
  JSON. Prefer complete, traceable output over a single oversized response.

Recommended test type mapping:

| Type | Use When |
| --- | --- |
| `smoke` | Minimal critical path proving the feature is basically usable. |
| `functional` | New-feature requirement and acceptance-criteria coverage. |
| `negative` | Invalid input, forbidden action, wrong state, or auth failure. |
| `boundary` | Limits and data-state edges such as empty, single, many, max. |
| `e2e` | Cross-module user flow across multiple product surfaces. |
| `regression` | Existing feature behavior that could break because of the new change. |

### 4. AI Case Review

ReviewerAgent checks the generated scenarios before human approval.

Checks:
- PRD alignment
- completeness and clarity
- missing positive/negative/boundary coverage
- traceability matrix
- PRD clarification needs

Output:
- `case_review`

Routing:
- pass: continue to QA Lead approval
- critical findings or low quality score: stop and report for revision
- needs revision: export draft JSON/CSV under `reports/drafts/` for inspection,
  but do not create official CSV/Excel test plan artifacts.

Severity model:
- Critical: missing release-blocking requirement, unsafe/invalid expectation, or
  test plan cannot be executed
- Major: important negative, role, boundary, or API-contract coverage is absent
- Minor: clarity, naming, tagging, or formatting improvement

### 5. QA Lead Approval

QA Lead reviews the generated scenarios before they become official.

Approval decisions:
- approve: continue to export and automation generation
- reject: stop and report feedback
- edit: treat as not approved until an edit workflow exists
- timeout: stop in CI; local auto-approval is allowed only when configured

Output:
- `approval`
- `approved`

### 6. Official Test Plan Export

The pipeline exports only approved test cases.

Output:
- CSV for lightweight sharing/import
- Excel for QA review and manual execution

Required columns:
- `Case ID`
- `Title`
- `Preconditions`
- `Steps`
- `Expected Result`
- `Priority`
- `Tags`
- `Platform`
- `AI Generated`
- `Regression Candidate`
- `Regression Risk Area`

Artifact owner:
- `testcase_export`

Rule:
- if export fails, the pipeline stops before codegen because the team does not
  have an official test plan artifact.

Recommended manual or future automated import:

```text
approved CSV/Excel -> QA Lead review -> TestRail/spreadsheet import -> automation codegen
```

`AI Generated` should stay in the exported artifact so the team can distinguish
AI-created cases from manually-authored or manually-edited cases.

### 7. Locator and Page Object Preparation

For web and mobile automation, prepare stable interaction contracts before
test-code generation.

Workflow:

```text
approved test cases
  -> inspect available URL/app screen when accessible
  -> collect stable selectors and screen elements
  -> create or update page-object helpers
  -> hand locator map to codegen
```

Rules:
- prefer existing helpers and page objects over raw selectors
- use stable IDs/accessibility labels/test IDs where available
- avoid storing credentials or environment secrets in generated tests
- when the target URL/app is not accessible, generate code with explicit TODO
  markers and fixture placeholders instead of inventing selectors

Future node:
- `locator_page_object`

### 8. Automation Generation

CodeGen consumes the same approved `testcase_output` used for CSV/Excel.

Output:
- `generated_files`

Rules:
- do not regenerate test cases
- do not hardcode credentials
- use `TestConfig`/test data classes for environment data
- use page-object or platform helper methods when available
- keep generated tests small enough to debug from a single failed case ID

### 9. Execution

Run generated/affected tests with the project venv.

Command standard:

```bash
PYTHONPATH=. ./venv/bin/python3.11 -m pytest [test_file] -v --tb=short
```

Output:
- `execution_results`
- `failures`
- pytest JSON report

### 10. Failure Analysis

DebugAgent runs only when execution fails.

Output:
- `bug_reports`

Rules:
- classify failures as product bug, test code issue, environment issue, or data
  issue
- Jira bug creation should remain explicit, not hidden inside analysis

### 11. Coverage Analysis

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

### 12. Post-Deployment Healing

Healing should be conservative. Its job is to repair brittle automation, not hide
product defects.

Workflow:

```text
failed test
  -> baseline rerun
  -> lightweight failure analysis
  -> safety check
  -> small repair attempt
  -> verification
  -> trace/UI diagnosis when needed
  -> surrender report when confidence remains low
```

Rules:
- stop immediately when the failure is likely backend/API/product instability
- do not edit unrelated passing steps
- prefer small locator/page-object repairs over rewriting a test
- limit automatic repair attempts so failures stay visible
- if no safe fix is found, add a clear report and leave the test for human review

## Node Contracts

### `source_intake`

Input:
- `feature`
- `platforms`
- `ticket_id`
- `story_text`
- optional `feature_url`
- optional `existing_test_cases`

Output:
- `source_bundle`

Rules:
- Normalizes all human, Jira, PRD, URL, and existing-test context.
- Downstream nodes read from `source_bundle` instead of each rediscovering
  source context.
- External sources that require unavailable credentials are recorded as
  inaccessible instead of blocking the whole workflow.
- Feature URL observation is optional and should be performed by a dedicated
  adapter/node when the target is reachable.

Future observed URL fields:
- page title
- visible labels and actions
- detected forms
- screenshots or trace path
- network/API hints when available
- observation warnings

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

### `case_review`

Input:
- `source_bundle.prd_content`
- `test_cases`

Output:
- `case_review`

Rules:
- Runs before human approval.
- Blocks approval when critical findings exist.
- Blocks approval when `overall_quality_score` is below the configured quality
  threshold.
- Produces a traceability matrix and revision recommendations for the team.

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

### Future `locator_page_object`

Input:
- approved `testcase_output`
- `platforms`
- optional `feature_url`
- existing platform helper files

Output:
- locator map
- page-object/helper update plan
- warnings for missing stable selectors

Rules:
- Runs before `codegen` for `web`, `android`, and `ios`.
- For `api`, this node is skipped.
- Must prefer existing helpers in `platforms/` and `skills/`.
- Must not require credentials in chat; use `.env`, `TestConfig`, and test data
  providers.

### Future `testrail_import`

Input:
- `testcase_exports.csv`
- approval metadata

Output:
- imported test case IDs
- import status
- skipped row report

Rules:
- This should be explicit and reversible.
- CSV/Excel remains the source artifact even when an external test management
  system is used.

### Future `healer_baseline`

Input:
- failed generated test path
- pytest failure context

Output:
- baseline failure classification
- retry evidence

Rules:
- Rerun the exact failing test before attempting any fix.
- If the rerun passes, classify as flaky and report without editing code.
- If backend/API instability is likely, stop and report instead of patching UI
  tests.

### Future `repair_decision`

Input:
- baseline failure classification
- trace/screenshot/DOM evidence when available
- target test file and helper files

Output:
- repair proposal
- confidence score
- changed files when applied

Rules:
- Apply only high-confidence, narrowly-scoped repairs.
- Prefer page-object/helper updates over inline selector churn.
- Limit automatic attempts; after repeated failure, surrender with evidence for
  human review.

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

## Recommended Implementation Order

Use this order to keep the architecture tidy while improving team value.

1. Persist full pipeline state JSON per run.
2. Add `run_id` to CSV/Excel export filenames.
3. Make `case_review` threshold configurable per mode: advisory locally,
   blocking in CI/release mode.
4. Add optional `feature_observe` for reachable URLs using the existing
   Playwright/web driver approach.
5. Add `testrail_import` or a manual import manifest without replacing CSV/Excel.
6. Add `locator_page_object` before codegen for web/mobile flows.
7. Split codegen by platform so API, web, and mobile generation can evolve
   independently.
8. Add conservative post-deployment healer flow with strict retry limits and
   surrender reports.

Do not implement all future nodes at once. Each node should land with:
- state keys in `AgentState`
- one contract test
- one CLI or pipeline integration path
- one artifact written to `reports/`
- documentation in this spec

## Architecture Review Notes

Current strengths:
- source intake creates a normalized context bundle
- AI case review runs before QA Lead approval
- approved `testcase_output` is reused by export and codegen
- CSV/Excel export is a separate graph node
- execution uses the project Python runtime
- downstream nodes no longer regenerate upstream artifacts
- orchestration contract tests cover the riskiest handoffs

Recommended next improvements:
- add retry/edit workflow for rejected approvals instead of stopping at report
- add `run_id` to exported CSV/Excel filenames
- persist full pipeline state as JSON for audit/debug replay
- split web/API/mobile codegen by platform instead of using only `platforms[0]`
- add CI mode that disables Telegram and uses deterministic approval policy
