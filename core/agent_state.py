"""
Shared state schema for the LangGraph QA pipeline orchestrator.
All agents read from and write to this single TypedDict.
"""
from __future__ import annotations
from typing import TypedDict, Any


class AgentState(TypedDict, total=False):
    # ── Input ────────────────────────────────────────────────────────
    ticket_id:            str           # Jira ticket / feature name
    feature:              str           # Human-readable feature name
    platforms:            list[str]     # ["web", "api", "mobile"]
    story_text:           str           # Raw requirements text
    feature_url:          str           # Optional implemented feature URL
    prd_url:              str           # Optional Confluence/PRD URL
    include_subtasks:     bool          # Include Jira subtasks in intake context

    # ── Source intake phase ─────────────────────────────────────────
    source_bundle:        dict          # Normalized Jira/PRD/URL/context bundle

    # ── Requirements phase ──────────────────────────────────────────
    acceptance_criteria:  list[str]     # Extracted AC summaries for prompts
    acceptance_criteria_details: list[dict]  # Full AC objects for traceability
    requirements_output:  dict          # Full requirements_agent output
    requirements_raw:     dict          # Backward-compatible alias

    # ── Test plan phase ─────────────────────────────────────────────
    test_plan:            dict          # TestPlanOutput serialised to dict
    techniques_used:      list[str]     # Techniques selected by test_plan_agent

    # ── Test case phase ─────────────────────────────────────────────
    test_cases:           list[dict]    # Generated test case dicts
    testcase_output:      Any           # TestCaseAgentOutput used by downstream agents
    confidence_score:     float         # 0.0–1.0 confidence derived from review coverage
    case_review:          dict          # AI review summary before human approval
    approved:             bool          # Legacy approval flag (kept for compat)
    approval:             dict          # Approval status, reviewer, feedback
    approval_feedback:    str           # Reviewer comment if rejected
    # ── Confidence-based async approval ─────────────────────────────
    approval_decision:    str           # "approve"|"reject"|"pending"|"escalated"
    approval_method:      str           # "auto"|"async_telegram"
    approval_id:          str           # Unique ID for file-backed pending approval
    approval_retry_count: int           # Auto-reject+regenerate cycle count
    rejection_feedback:   str           # Feedback forwarded back to testcase node

    # ── Test case export phase ──────────────────────────────────────
    testcase_exports:     dict[str, str]  # {csv: path, excel: path}
    draft_exports:        dict[str, str]  # Draft artifacts for needs_revision cases

    # ── Automation readiness phase ─────────────────────────────────
    automation_evidence:  dict[str, Any]  # Explicit curl/locator/step evidence for codegen
    automation_readiness: dict[str, Any]  # Readiness report before codegen

    # ── Code generation phase ───────────────────────────────────────
    generated_files:      dict[str, str]  # {relative_path: absolute_path}

    # ── Execution phase ─────────────────────────────────────────────
    execution_results:    dict[str, Any]  # {platform: {passed, failed, errors}}
    failures:             list[dict]      # Raw failure contexts

    # ── Debug phase ─────────────────────────────────────────────────
    bug_reports:          list[dict]    # BugReport dicts per failure

    # ── Skill gap phase ─────────────────────────────────────────────
    coverage_gaps:        list[str]     # Untested scenarios
    coverage_percentage:  float         # 0-100
    gap_report_path:      str           # Path to saved gap report

    # ── Pipeline metadata ───────────────────────────────────────────
    current_phase:        str           # Current node name
    error:                Any           # Last error payload
    run_id:               str           # Unique pipeline run ID
