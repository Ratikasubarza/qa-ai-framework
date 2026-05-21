"""
Artifact writer — canonical run-scoped directory layout.

All pipeline artifact writers should use get_run_dir() so artifacts are
grouped by run_id under reports/runs/<run_id>/<artifact_type>/.

Backward-compatible: the global legacy paths (reports/excel/, reports/gap_reports/,
reports/drafts/) are still used by the CLI and global singletons. Pipeline nodes
call get_run_dir() to get the run-scoped path and pass it to writers.

Canonical layout:
  reports/runs/<run_id>/
    source/           — source_bundle.json
    requirements/     — requirements.json, requirements.md
    test_plan/        — test_plan.json, test_plan.xlsx, test_plan.md
    test_cases/       — test_cases.json, test_cases.csv, test_cases.xlsx
    review/           — review_report.json, review_report.md
    codegen/          — generated_files.json, codegen_summary.md
    execution/        — execution_result.json, allure/
    debug/            — debug_report.json, debug_summary.md
    flaky/            — flaky_report.json, flaky_report.csv
    skill_gap/        — skill_gap_report.json, skill_gap_summary.md
    jira/             — bug_ticket_recommendations.json, qa_task_recommendations.json
  reports/runs/<run_id>/final_summary.md
"""
from __future__ import annotations

import json
import structlog
from datetime import datetime
from pathlib import Path
from typing import Any

logger = structlog.get_logger(__name__)

RUNS_ROOT = Path("reports/runs")

ARTIFACT_TYPES = frozenset({
    "source",
    "requirements",
    "test_plan",
    "test_cases",
    "review",
    "codegen",
    "execution",
    "debug",
    "flaky",
    "skill_gap",
    "jira",
})


def get_run_dir(run_id: str, artifact_type: str) -> Path:
    """
    Return (and create) the canonical directory for a run artifact.

    Example: get_run_dir("20260518_143000", "test_cases")
             → reports/runs/20260518_143000/test_cases/
    """
    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError(
            f"Unknown artifact_type '{artifact_type}'. "
            f"Must be one of: {sorted(ARTIFACT_TYPES)}"
        )
    path = RUNS_ROOT / run_id / artifact_type
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_run_root(run_id: str) -> Path:
    """Return (and create) the root directory for a run."""
    path = RUNS_ROOT / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any) -> Path:
    """Write data as indented JSON to path. Returns path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    logger.info("artifact_written", path=str(path), type="json")
    return path


def write_markdown(path: Path, content: str) -> Path:
    """Write markdown content to path. Returns path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info("artifact_written", path=str(path), type="md")
    return path


def write_final_summary(run_id: str, state: dict) -> Path:
    """
    Write a final_summary.md to the run root directory.
    Safe subset of state — no secrets, no raw response bodies.
    """
    run_root = get_run_root(run_id)
    path = run_root / "final_summary.md"

    feature      = state.get("feature", "N/A")
    ticket       = state.get("ticket_id", "N/A")
    platforms    = ", ".join(state.get("platforms") or [])
    tc_count     = len(state.get("test_cases") or [])
    failures     = len(state.get("failures") or [])
    bugs         = len(state.get("bug_reports") or [])
    gaps         = len(state.get("coverage_gaps") or [])
    coverage     = state.get("coverage_percentage") or 0.0
    case_review  = state.get("case_review") or {}
    cr_score     = case_review.get("quality_score", "N/A")
    cr_status    = case_review.get("status", "N/A")
    phase        = state.get("current_phase", "N/A")
    approval     = state.get("approval_decision", "N/A")
    exports      = state.get("testcase_exports") or {}
    generated    = state.get("generated_files") or {}
    error        = state.get("error")
    status       = "PASSED" if not failures and not error else "FAILED"
    timestamp    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"# QA Pipeline Final Summary — {status}",
        f"",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Run ID | `{run_id}` |",
        f"| Feature | {feature} |",
        f"| Ticket | {ticket} |",
        f"| Platforms | {platforms} |",
        f"| Generated | {timestamp} |",
        f"| Last Phase | {phase} |",
        f"| Approval | {approval} |",
        f"",
        f"## Test Results",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Test Cases | {tc_count} |",
        f"| Failures | {failures} |",
        f"| Bugs Found | {bugs} |",
        f"| Coverage Gaps | {gaps} |",
        f"| Coverage % | {coverage:.1f}% |",
        f"| Case Review Score | {cr_score} |",
        f"| Case Review Status | {cr_status} |",
    ]

    if exports:
        lines += ["", "## Test Case Exports", ""]
        for name, path_str in exports.items():
            lines.append(f"- `{name}`: `{path_str}`")

    if generated:
        lines += ["", "## Generated Test Files", ""]
        for name in list(generated.keys())[:10]:
            lines.append(f"- `{name}`")

    if error:
        err_msg = str(error.get("message", error) if isinstance(error, dict) else error)
        lines += ["", "## Pipeline Error", "", f"```", err_msg[:300], "```"]

    write_markdown(path, "\n".join(lines))
    return path
