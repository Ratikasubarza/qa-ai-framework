# Agent Flow Diagram — QA AI Framework Phase 9

## LangGraph Pipeline Flow

```
START
  │
  ▼
[node_source_intake]
  Source: Jira ticket + Confluence PRD + feature URL
  Output: source_bundle (prd_content, jira_fetched)
  │
  ├─ error → [node_report] → [node_jira_update] → END
  │
  ▼
[node_requirements]
  Agent: RequirementsAgent
  Input: source_bundle.prd_content or Jira story
  Output: acceptance_criteria (list[str]), criteria_details
  Fallback: empty AC list, pipeline continues
  │
  ▼
[node_testcase]  (async)
  Agent: TestCaseAgent
  Input: TestCaseAgentInput (feature, platforms, AC)
  Output: TestCaseAgentOutput (scenarios, confidence_score)
  Retry: up to 3× on rejection (approval_retry_count)
  │
  ▼
[node_case_review]
  Agent: ReviewerAgent
  Input: test_cases[], prd_content, platforms
  Output: quality_score (0–10), coverage_percentage, confidence_score
  Gate: quality_score ≥ 7.0 AND no blocking findings
  │
  ├─ needs_revision → [node_report] → [node_jira_update] → END
  │
  ▼
[node_approval]  (async, 3-tier)
  ┌─ Tier 1: confidence ≥ 0.85 AND regression → AUTO-APPROVE ──────────────┐
  ├─ Tier 2: confidence 0.60–0.84 → ASYNC TELEGRAM → pipeline pauses → END │
  │          (resumes via Telegram button or `cli.py approve`)              │
  └─ Tier 3: confidence < 0.60 → AUTO-REJECT → back to node_testcase ──────┘
             (max 3 retries, then escalate to Telegram)
  │
  ▼ (approved)
[node_codegen]
  Agent: CodeGeneratorAgent
  Input: TestCaseAgentOutput, Platform, automation_evidence
  Output: generated_files (dict path → content)
  │
  ├─ no files → [node_skill_gap]
  │
  ▼
[node_execute]
  Runs: pytest subprocess per generated file
  Output: execution_results, failures[]
  │
  ├─ failures → [node_debug]
  │               Agent: DebugAgent
  │               Output: bug_reports[]
  │               ↓
  └─ no failures → [node_skill_gap]
                     ↓
[node_skill_gap]
  Agent: SkillGapAgent
  Input: acceptance_criteria, test_cases
  Output: coverage_percentage, coverage_gaps, gap_report_path
  │
  ▼
[node_report]
  Sends: Telegram summary to qa_ops channel
  Posts: GitHub PR comment (if github_pr_number in state)
  Output: notifications[]
  │
  ▼
[node_jira_update]
  Transitions: ticket → DONE (0 failures) or IN TEST (failures)
  Adds: Jira comment with failure summary
  │
  ▼
END
```

## Orphan nodes (connected to graph but currently unreachable)

| Node | Status | Note |
|------|--------|------|
| `testcase_export` | Unreachable | `route_after_approval` goes to `codegen` directly, skipping export |
| `automation_readiness_gate` | Unreachable | Same reason — no incoming edge from approval path |

**Impact:** test case CSV/Excel export and automation readiness check do not run in the normal approved path. Export only works via `cli.py export`.

**Fix required:** `route_after_approval` should return `"testcase_export"` instead of `"codegen"`, then `testcase_export → automation_readiness_gate → codegen`.

## State keys (AgentState TypedDict)

| Key | Set by | Used by |
|-----|--------|---------|
| `feature` | pipeline entry | all nodes |
| `ticket_id` | pipeline entry | jira_update, requirements |
| `acceptance_criteria` | node_requirements | node_testcase, node_skill_gap |
| `test_cases` | node_testcase | node_case_review, node_approval, node_skill_gap |
| `confidence_score` | node_case_review | node_approval |
| `approval_decision` | node_approval | route_after_approval |
| `approval_retry_count` | node_approval | node_approval (max 3) |
| `generated_files` | node_codegen | node_execute |
| `failures` | node_execute | node_debug, node_jira_update, node_report |
| `bug_reports` | node_debug | node_report |
| `coverage_percentage` | node_skill_gap | node_report |
| `gap_report_path` | node_skill_gap | node_report |
| `github_pr_number` | pipeline entry | node_report |

## Agent → LLM tier mapping

| Agent | Tier | Dev model | Prod model |
|-------|------|-----------|-----------|
| TestCaseAgent | standard | gpt-oss-20b | claude-sonnet |
| ReviewerAgent | complex | gpt-oss-120b | claude-opus |
| CodeGeneratorAgent | standard | gpt-oss-20b | claude-sonnet |
| DebugAgent | standard | gpt-oss-20b | claude-sonnet |
| LocatorAgent | fast | nemotron-nano | claude-haiku |
| FlakyTestAgent | fast | nemotron-nano | claude-haiku |
| RequirementsAgent | standard | gpt-oss-20b | claude-sonnet |
| SkillGapAgent | standard | gpt-oss-20b | claude-sonnet |
