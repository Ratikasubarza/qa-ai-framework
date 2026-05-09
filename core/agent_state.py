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

    # ── Requirements phase ──────────────────────────────────────────
    acceptance_criteria:  list[str]     # Extracted AC list
    requirements_raw:     dict          # Full requirements_agent output

    # ── Test case phase ─────────────────────────────────────────────
    test_cases:           list[dict]    # Generated test case dicts
    approved:             bool          # Telegram approval gate
    approval_feedback:    str           # Reviewer comment if rejected

    # ── Code generation phase ───────────────────────────────────────
    generated_files:      list[str]     # Paths to generated test files

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
    error:                str | None    # Last error message
    run_id:               str           # Unique pipeline run ID