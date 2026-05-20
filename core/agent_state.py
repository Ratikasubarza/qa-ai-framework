"""
Shared state schema for the LangGraph QA pipeline orchestrator.
All agents read from and write to this single TypedDict.

Accumulative list fields (failures, bug_reports, coverage_gaps) are typed with
operator.add as the LangGraph reducer so that parallel node writes concatenate
rather than overwrite. All other fields use last-write-wins semantics.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    # ── Input ────────────────────────────────────────────────────────
    ticket_id:            Optional[str]        # Jira ticket / feature name
    feature:              Optional[str]        # Human-readable feature name
    platforms:            Optional[list[str]]  # ["web", "api", "mobile"]
    story_text:           Optional[str]        # Raw requirements text
    feature_url:          Optional[str]        # Optional implemented feature URL
    prd_url:              Optional[str]        # Optional Confluence/PRD URL
    include_subtasks:     bool                 # Include Jira subtasks in intake context

    # ── Source intake phase ─────────────────────────────────────────
    source_bundle:        Optional[dict]       # Normalized Jira/PRD/URL/context bundle

    # ── Requirements phase ──────────────────────────────────────────
    acceptance_criteria:         Optional[list[str]]   # Extracted AC summaries for prompts
    acceptance_criteria_details: Optional[list[dict]]  # Full AC objects for traceability
    requirements_output:         Optional[dict]        # Full requirements_agent output
    requirements_raw:            Optional[dict]        # Backward-compatible alias

    # ── Test plan phase ─────────────────────────────────────────────
    test_plan:            Optional[dict]       # TestPlanOutput serialised to dict
    techniques_used:      Optional[list[str]]  # Techniques selected by test_plan_agent

    # ── Test case phase ─────────────────────────────────────────────
    test_cases:           Optional[list[dict]]  # Generated test case dicts
    testcase_output:      Any                   # TestCaseAgentOutput used by downstream
    confidence_score:     float                 # 0.0–1.0 confidence derived from review
    case_review:          Optional[dict]        # AI review summary before human approval
    approved:             bool                  # Legacy approval flag (kept for compat)
    approval:             Optional[dict]        # Approval status, reviewer, feedback
    approval_feedback:    Optional[str]         # Reviewer comment if rejected

    # ── Confidence-based async approval ─────────────────────────────
    approval_decision:    Optional[str]         # "approve"|"reject"|"pending"|"escalated"
    approval_method:      Optional[str]         # "auto"|"async_telegram"
    approval_id:          Optional[str]         # Unique ID for file-backed pending approval
    approval_retry_count: int                   # Auto-reject+regenerate cycle count
    rejection_feedback:   Optional[str]         # Feedback forwarded back to testcase node

    # ── Test case export phase ──────────────────────────────────────
    testcase_exports:     Optional[dict[str, str]]  # {csv: path, excel: path}
    draft_exports:        Optional[dict[str, str]]  # Draft artifacts for needs_revision

    # ── Automation readiness phase ─────────────────────────────────
    automation_evidence:  Optional[dict[str, Any]]  # Explicit curl/locator/step evidence
    automation_readiness: Optional[dict[str, Any]]  # Readiness report before codegen

    # ── Code generation phase ───────────────────────────────────────
    generated_files:      Optional[dict[str, str]]  # {relative_path: absolute_path}

    # ── Execution phase ─────────────────────────────────────────────
    execution_results:    Optional[dict[str, Any]]  # {platform: {passed, failed, errors}}

    # Accumulative: operator.add reducer — parallel nodes concatenate, not overwrite
    failures:   Annotated[list[dict], operator.add]  # Raw failure contexts
    bug_reports: Annotated[list[dict], operator.add]  # BugReport dicts per failure

    # ── Flaky analysis phase ─────────────────────────────────────────
    flaky_results:        Optional[list[dict]]   # FlakyTestResult dicts

    # ── Skill gap phase — also accumulative ─────────────────────────
    coverage_gaps: Annotated[list[str], operator.add]  # Untested scenarios
    coverage_percentage:  float                  # 0-100
    gap_report_path:      Optional[str]          # Path to saved gap report

    # ── Coverage report phase ───────────────────────────────────────
    coverage_report:      Optional[dict]         # Full gap report from skill_gap node

    # ── Notifications ───────────────────────────────────────────────
    # Message passing (LangGraph 0.2.x add_messages reducer)
    messages: Annotated[list[BaseMessage], add_messages]

    notifications:        Optional[list[dict]]   # Sent channel notifications log

    # ── GitHub integration ──────────────────────────────────────────
    github_pr_number:     Optional[int]          # Optional PR number for GitHub comment

    # ── Pipeline metadata ───────────────────────────────────────────
    current_phase:        Optional[str]          # Current node name
    error:                Any                    # Last error payload
    run_id:               Optional[str]          # Unique pipeline run ID
    retry_count:          int                    # Pipeline-level retry counter
