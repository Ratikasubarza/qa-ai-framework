"""
Phase 9 — Full LangGraph QA Pipeline Orchestrator.

This module owns cross-agent coordination. Agents create artifacts; the graph
decides when an artifact is approved, reused, skipped, or reported.

Flow:
  START → source_intake → requirements → testcase → case_review → approval
        → testcase_export → codegen → execute → debug (on failure)
        → skill_gap → report → END
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import httpx
import structlog

from core.agent_state import AgentState
from core.automation_readiness import check_automation_readiness
from core.case_review import normalize_review_scope
from core.source_intake import build_source_intake_state

logger = structlog.get_logger(__name__)

PYTHON_BIN = "./venv/bin/python3.11"
MAX_APPROVAL_ATTEMPTS = 1
CASE_REVIEW_MIN_SCORE = 7.0


def _criteria_summary(criteria: list[Any]) -> list[str]:
    """Return prompt-ready AC summaries while preserving details elsewhere."""
    summaries: list[str] = []
    for item in criteria:
        if isinstance(item, str):
            if item.strip():
                summaries.append(item.strip())
        elif isinstance(item, dict):
            summary = item.get("summary") or item.get("description") or item.get("title")
            if summary:
                summaries.append(str(summary).strip())
    return summaries


def _scenario_to_dict(scenario: Any) -> dict:
    if hasattr(scenario, "model_dump"):
        data = scenario.model_dump(mode="json")
    elif isinstance(scenario, dict):
        data = dict(scenario)
    else:
        data = {"name": str(scenario)}

    data["scenario_id"] = data.get("scenario_id") or data.get("case_id") or "TC-UNKNOWN"
    data["name"] = (data.get("name") or data.get("title") or "Unnamed scenario").strip()
    return data


def _generated_file_paths(generated_files: Any) -> list[str]:
    if isinstance(generated_files, dict):
        return [str(path) for path in generated_files.values()]
    if isinstance(generated_files, list):
        return [str(path) for path in generated_files]
    return []


def _approval_payload(status: str, **extra: Any) -> dict:
    return {
        "status": status,
        "reviewed_at": datetime.now().isoformat(),
        **extra,
    }


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _error_message(error: Any) -> str:
    if isinstance(error, dict):
        return str(error.get("message", error))
    return str(error)


def _normalize_review_score(score: Any) -> tuple[float, float]:
    raw_score = _as_float(score, 0.0)
    if raw_score > 10:
        return round(raw_score / 10, 2), raw_score
    return raw_score, raw_score


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return slug or "feature"


def _write_case_review_draft_exports(state: AgentState, review: dict) -> dict[str, str]:
    output_dir = Path("reports/drafts")
    output_dir.mkdir(parents=True, exist_ok=True)

    feature_slug = _slugify(state.get("feature", "feature"))
    run_id = state.get("run_id") or datetime.now().strftime("%Y%m%d_%H%M%S")
    base = output_dir / f"test_plan_{feature_slug}_{run_id}_needs_revision"
    test_cases = state.get("test_cases") or []

    json_path = base.with_suffix(".json")
    csv_path = base.with_suffix(".csv")
    payload = {
        "feature": state.get("feature"),
        "run_id": run_id,
        "status": "needs_revision",
        "case_review": review,
        "test_cases": test_cases,
    }
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "scenario_id", "name", "precondition", "steps", "expected_result",
            "priority", "test_type", "platforms", "tags",
            "regression_candidate", "regression_risk_area",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for case in test_cases:
            row = {field: case.get(field, "") for field in fieldnames}
            for field in ["steps", "platforms", "tags", "regression_risk_area"]:
                if isinstance(row[field], list):
                    row[field] = json.dumps(row[field], ensure_ascii=False)
            writer.writerow(row)

    logger.info("case_review_draft_exported", json=str(json_path), csv=str(csv_path))
    return {"json": str(json_path), "csv": str(csv_path)}


# ── Node: Source Intake ─────────────────────────────────────────────────────
def node_source_intake(state: AgentState) -> AgentState:
    logger.info("node_start", node="source_intake", feature=state.get("feature"))
    return build_source_intake_state(state, logger)


# ── Node: Requirements ───────────────────────────────────────────────────────
def node_requirements(state: AgentState) -> AgentState:
    include_subtasks = bool(state.get("include_subtasks"))
    logger.info(
        "node_start",
        node="requirements",
        ticket=state.get("ticket_id"),
        include_subtasks=include_subtasks,
        confluence_url=state.get("prd_url") or None,
    )

    try:
        from agents.requirements_agent import requirements_agent

        source_bundle = state.get("source_bundle") or {}
        # prd_content already has Confluence text merged in by source_intake when prd_url is set
        # subtask details are merged in when include_subtasks=True
        source_text = source_bundle.get("prd_content") or state.get("story_text", "")

        if source_bundle.get("jira_source", {}).get("fetched") or source_bundle.get("prd_source", {}).get("fetched"):
            logger.info(
                "requirements_source",
                jira_fetched=bool(source_bundle.get("jira_source", {}).get("fetched")),
                confluence_fetched=bool(source_bundle.get("prd_source", {}).get("fetched")),
                subtasks_included=include_subtasks,
            )
            result = requirements_agent.run_from_text(
                feature=state.get("feature", ""),
                story_text=source_text,
                parent_key=state.get("ticket_id", ""),
            )
        elif state.get("ticket_id"):
            result = requirements_agent.run_from_jira(state["ticket_id"])
        else:
            result = requirements_agent.run_from_text(
                feature=state.get("feature", ""),
                story_text=source_text,
                parent_key="",
            )

        criteria_details = (
            result.get("criteria")
            or result.get("acceptance_criteria_details")
            or []
        )
        summaries = _criteria_summary(
            criteria_details or result.get("acceptance_criteria") or []
        )

        return {
            **state,
            "current_phase": "requirements",
            "acceptance_criteria": summaries,
            "acceptance_criteria_details": criteria_details,
            "requirements_output": result,
            "requirements_raw": result,
            "error": None,
        }
    except Exception as e:
        logger.error("node_failed", node="requirements", error=str(e))
        return {
            **state,
            "current_phase": "requirements",
            "error": {"phase": "requirements", "message": str(e)},
        }


# ── Node: Test Case Generation ───────────────────────────────────────────────
async def node_testcase(state: AgentState) -> AgentState:
    from agents.test_case_agent import test_case_agent
    from core.agent_contracts import Platform, TestCaseAgentInput

    logger.info("node_start", node="testcase", feature=state.get("feature"))

    try:
        platforms = [Platform(p) for p in (state.get("platforms") or ["web"])]
        inp = TestCaseAgentInput(
            feature=state.get("feature", ""),
            description=state.get("story_text", state.get("feature", "")),
            platforms=platforms,
            acceptance_criteria=state.get("acceptance_criteria", []),
            jira_story_key=state.get("ticket_id") or None,
            confluence_page_url=state.get("prd_url") or None,
        )
        output = await test_case_agent.run(inp, require_approval=False)
        if not output.scenarios:
            raise ValueError(
                "TestCaseAgent generated 0 scenarios. "
                f"coverage_summary={output.coverage_summary or 'N/A'}"
            )
        test_cases = [_scenario_to_dict(s) for s in output.scenarios]

        return {
            **state,
            "current_phase": "testcase",
            "testcase_output": output,
            "test_cases": test_cases,
            "approved": False,
            "approval": _approval_payload("pending", attempt=0),
            "error": None,
        }
    except Exception as e:
        logger.error("node_failed", node="testcase", error=str(e))
        return {
            **state,
            "current_phase": "testcase",
            "test_cases": [],
            "approved": False,
            "approval": _approval_payload("failed", message=str(e)),
            "error": {"phase": "testcase", "message": str(e)},
        }


# ── Node: Approval Gate ─────────────────────────────────────────────────────
def node_case_review(state: AgentState) -> AgentState:
    from agents.reviewer_agent import reviewer_agent

    logger.info("node_start", node="case_review", feature=state.get("feature"))

    try:
        test_cases = state.get("test_cases") or []
        if not test_cases:
            raise ValueError("No test cases available for AI case review.")

        source_bundle = state.get("source_bundle") or {}
        prd_content = source_bundle.get("prd_content") or state.get("story_text", "")
        platforms = state.get("platforms") or source_bundle.get("platforms") or ["web"]
        report = reviewer_agent.review(
            prd_content=prd_content,
            test_cases_json=test_cases,
            feature=state.get("feature", "Feature"),
            target_platforms=platforms,
        )

        quality_score, raw_quality_score = _normalize_review_score(
            report.overall_quality_score
        )
        scope_review = normalize_review_scope(
            missing_test_cases=report.missing_test_cases,
            detailed_findings=report.detailed_findings,
            target_platforms=platforms,
        )
        scope_summary = scope_review["summary"]
        review = {
            "status": "passed",
            "quality_score": quality_score,
            "quality_score_raw": raw_quality_score,
            "coverage_percentage": report.coverage_percentage,
            "target_platforms": platforms,
            "findings": {
                "critical": report.findings_critical,
                "major": report.findings_major,
                "minor": report.findings_minor,
            },
            "scope_summary": scope_summary,
            "missing_test_cases": scope_review["missing_test_cases"],
            "detailed_findings": scope_review["detailed_findings"],
            "prd_clarifications": report.prd_clarifications,
            "recommendation": report.recommendation,
            "traceability_matrix": report.traceability_matrix,
        }

        if (
            scope_summary["blocking_critical_count"] > 0
            or scope_summary["blocking_missing_count"] > 0
            or scope_summary["security_blocker_count"] > 0
            or quality_score < CASE_REVIEW_MIN_SCORE
        ):
            review["status"] = "needs_revision"
            draft_exports = _write_case_review_draft_exports(state, review)
            return {
                **state,
                "current_phase": "case_review",
                "case_review": review,
                "draft_exports": draft_exports,
                "error": {
                    "phase": "case_review",
                    "message": (
                        "AI case review did not pass quality gate: "
                        f"score={quality_score}, "
                        f"blocking_critical={scope_summary['blocking_critical_count']}, "
                        f"blocking_missing={scope_summary['blocking_missing_count']}, "
                        f"security_blockers={scope_summary['security_blocker_count']}"
                    ),
                },
            }

        return {
            **state,
            "current_phase": "case_review",
            "case_review": review,
            "error": None,
        }
    except Exception as e:
        logger.error("node_failed", node="case_review", error=str(e))
        return {
            **state,
            "current_phase": "case_review",
            "case_review": {"status": "failed", "message": str(e)},
            "error": {"phase": "case_review", "message": str(e)},
        }


# ── Node: Approval Gate ─────────────────────────────────────────────────────
async def node_approval(state: AgentState) -> AgentState:
    """
    Single approval gate for orchestrated runs.

    TestCaseAgent approval is disabled in node_testcase so the graph owns the
    decision and guarantees codegen consumes the same reviewed artifact.
    """
    logger.info("node_start", node="approval")

    from config.settings import settings

    output = state.get("testcase_output")
    test_cases = state.get("test_cases") or []
    attempt = int((state.get("approval") or {}).get("attempt", 0)) + 1

    if not test_cases or output is None:
        return {
            **state,
            "current_phase": "approval",
            "approved": False,
            "approval": _approval_payload(
                "rejected",
                attempt=attempt,
                reason="no_test_cases",
                feedback="No test cases were generated.",
            ),
            "error": {"phase": "approval", "message": "No test cases were generated."},
        }

    if not settings.approval_required:
        logger.info("approval_auto", reason="settings.approval_required=false")
        return {
            **state,
            "current_phase": "approval",
            "approved": True,
            "approval": _approval_payload("auto_approved", attempt=attempt),
        }

    try:
        from core.telegram_bot import telegram_bot
        from core.workflows.approval_workflow import review_queue

        # Bot MUST run in this event loop — it shares review_queue (in-memory asyncio.Event).
        # start_polling() is idempotent; stop_polling() is called in finally.
        telegram_bot.set_review_queue(review_queue)
        await telegram_bot.start_polling()

        item = review_queue.enqueue(
            agent_name="orchestrator.testcase_approval",
            payload={
                "feature": state.get("feature", ""),
                "test_cases": test_cases,
                "run_id": state.get("run_id", ""),
            },
        )
        await telegram_bot.send_test_cases_for_review(
            output_id=item.output_id,
            feature=state.get("feature", ""),
            scenarios=output.scenarios,
            model_used=output.model_used,
        )

        feedback = await item.wait(timeout=300.0)
        status = feedback.decision.value
        approved = status == "approve"

        return {
            **state,
            "current_phase": "approval",
            "approved": approved,
            "approval": _approval_payload(
                "approved" if approved else status,
                attempt=attempt,
                output_id=item.output_id,
                reviewer_id=feedback.reviewer_id,
                rejection_reason=(
                    feedback.rejection_reason.value
                    if feedback.rejection_reason else None
                ),
                feedback=feedback.corrected_output,
            ),
            "approval_feedback": feedback.corrected_output or "",
            "error": None if approved else {
                "phase": "approval",
                "message": f"Test cases were not approved: {status}",
            },
        }
    except Exception as e:
        logger.error("node_failed", node="approval", error=str(e))
        return {
            **state,
            "current_phase": "approval",
            "approved": False,
            "approval": _approval_payload("failed", attempt=attempt, message=str(e)),
            "error": {"phase": "approval", "message": str(e)},
        }
    finally:
        # Always stop polling so the httpx session is released and the Application
        # can be restarted cleanly on the next pipeline run.
        try:
            from core.telegram_bot import telegram_bot as _tb
            await _tb.stop_polling()
        except Exception:
            pass


# ── Node: Test Case Export ──────────────────────────────────────────────────
def node_testcase_export(state: AgentState) -> AgentState:
    from core.agent_contracts import TestCaseAgentOutput
    from skills.reporting.excel_writer import excel_writer

    logger.info("node_start", node="testcase_export", feature=state.get("feature"))

    try:
        output = state.get("testcase_output")
        if output is None:
            raise ValueError("Missing approved testcase_output in pipeline state.")
        if isinstance(output, dict):
            output = TestCaseAgentOutput.model_validate(output)

        paths = excel_writer.write_both(output)
        exports = {name: str(path) for name, path in paths.items()}

        return {
            **state,
            "current_phase": "testcase_export",
            "testcase_output": output,
            "testcase_exports": exports,
            "error": None,
        }
    except Exception as e:
        logger.error("node_failed", node="testcase_export", error=str(e))
        return {
            **state,
            "current_phase": "testcase_export",
            "testcase_exports": {},
            "error": {"phase": "testcase_export", "message": str(e)},
        }


# ── Node: Code Generation ───────────────────────────────────────────────────
def node_automation_readiness(state: AgentState) -> AgentState:
    logger.info("node_start", node="automation_readiness", feature=state.get("feature"))
    readiness = check_automation_readiness(state)
    if readiness["codegen_allowed"]:
        return {
            **state,
            "current_phase": "automation_readiness",
            "automation_readiness": readiness,
            "error": None,
        }

    return {
        **state,
        "current_phase": "automation_readiness",
        "automation_readiness": readiness,
        "generated_files": {},
        "error": {
            "phase": "automation_readiness",
            "message": "Automation codegen blocked: executable flow evidence is incomplete.",
            "missing_evidence": readiness["missing_evidence"],
        },
    }


# ── Node: Code Generation ───────────────────────────────────────────────────
def node_codegen(state: AgentState) -> AgentState:
    from agents.code_generator_agent import code_generator_agent
    from core.agent_contracts import Platform, TestCaseAgentOutput

    logger.info("node_start", node="codegen", feature=state.get("feature"))

    try:
        output = state.get("testcase_output")
        if output is None:
            raise ValueError("Missing approved testcase_output in pipeline state.")
        if isinstance(output, dict):
            output = TestCaseAgentOutput.model_validate(output)

        platforms = [Platform(p) for p in (state.get("platforms") or ["web"])]
        saved = code_generator_agent.run(
            output,
            platforms[0],
            automation_evidence=state.get("automation_evidence") or {},
        )

        return {
            **state,
            "current_phase": "codegen",
            "testcase_output": output,
            "generated_files": saved,
            "error": None,
        }
    except Exception as e:
        logger.error("node_failed", node="codegen", error=str(e))
        return {
            **state,
            "current_phase": "codegen",
            "generated_files": {},
            "error": {"phase": "codegen", "message": str(e)},
        }


# ── Node: Test Execution ────────────────────────────────────────────────────
def node_execute(state: AgentState) -> AgentState:
    """Run generated test files via pytest, collect results."""
    logger.info("node_start", node="execute")
    files = _generated_file_paths(state.get("generated_files") or {})
    results: dict[str, dict] = {}
    failures: list[dict] = []

    for fpath in files:
        path = Path(fpath)
        if not path.exists():
            failures.append({
                "test_file": fpath,
                "error_message": "Generated test file does not exist.",
                "platform": (state.get("platforms") or ["web"])[0],
                "test_name": path.stem,
                "location": fpath,
            })
            continue

        report_path = Path("reports") / f"pytest_{path.stem}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        run = subprocess.run(
            [
                PYTHON_BIN,
                "-m",
                "pytest",
                fpath,
                "-v",
                "--tb=short",
                "--json-report",
                f"--json-report-file={report_path}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        passed = run.returncode == 0
        results[fpath] = {
            "passed": passed,
            "stdout": run.stdout[-4000:],
            "stderr": run.stderr[-4000:],
            "returncode": run.returncode,
            "json_report": str(report_path),
        }
        if not passed:
            failures.append({
                "test_file": fpath,
                "error_message": (run.stdout + "\n" + run.stderr)[-1000:],
                "platform": (state.get("platforms") or ["web"])[0],
                "test_name": path.stem,
                "location": fpath,
                "json_report": str(report_path),
            })

    logger.info("execute_complete", files=len(files), failures=len(failures))
    return {
        **state,
        "current_phase": "execute",
        "execution_results": results,
        "failures": failures,
    }


# ── Node: Debug Agent ───────────────────────────────────────────────────────
def node_debug(state: AgentState) -> AgentState:
    from agents.debug_agent import FailureContext, debug_agent

    logger.info("node_start", node="debug", failures=len(state.get("failures", [])))

    bug_reports = []
    for failure in state.get("failures") or []:
        ctx = FailureContext(
            test_name=failure.get("test_name", "unknown"),
            error_message=failure.get("error_message", ""),
            platform=failure.get("platform", "web"),
            location=failure.get("location", ""),
            stack_trace=failure.get("stderr", ""),
        )
        report = debug_agent.analyze(ctx)
        bug_reports.append({
            "title": report.title,
            "severity": report.severity,
            "bug_type": report.bug_type,
            "root_cause": report.root_cause,
            "steps": report.steps_to_reproduce,
            "jira_key": report.jira_key,
        })

    return {**state, "current_phase": "debug", "bug_reports": bug_reports}


# ── Node: Skill Gap Analysis ────────────────────────────────────────────────
def node_skill_gap(state: AgentState) -> AgentState:
    from agents.skill_gap_agent import skill_gap_agent

    logger.info("node_start", node="skill_gap")

    gap = skill_gap_agent.analyze(
        acceptance_criteria=state.get("acceptance_criteria", []),
        test_cases=state.get("test_cases", []),
        feature=state.get("feature", ""),
    )
    path = skill_gap_agent.save_report(
        gap_data=gap,
        feature=state.get("feature", "unknown"),
        run_id=state.get("run_id", ""),
    )
    coverage_report = {
        **gap,
        "report_path": path,
    }
    return {
        **state,
        "current_phase": "skill_gap",
        "coverage_report": coverage_report,
        "coverage_gaps": gap.get("missing_scenarios", []),
        "coverage_percentage": gap.get("coverage_percentage", 0.0),
        "gap_report_path": path,
    }


# ── Node: Report ────────────────────────────────────────────────────────────
def node_report(state: AgentState) -> AgentState:
    """Send final Telegram summary report."""
    import os

    logger.info("node_start", node="report")

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_QA_OPS_CHAT_ID")

    failures = state.get("failures") or []
    bugs = state.get("bug_reports") or []
    gaps = state.get("coverage_gaps") or []
    case_review = state.get("case_review") or {}
    automation_readiness = state.get("automation_readiness") or {}
    test_cases = state.get("test_cases") or []
    testcase_exports = state.get("testcase_exports") or {}
    generated_files = state.get("generated_files") or {}
    coverage = _as_float(
        state.get("coverage_percentage")
        if state.get("coverage_percentage") is not None
        else case_review.get("coverage_percentage"),
        0.0,
    )
    status = "PASSED" if not failures and not state.get("error") else "FAILED"

    bug_lines = "\n".join(f"  - [{b['severity']}] {b['title'][:60]}" for b in bugs[:5])
    gap_lines = "\n".join(f"  - {g[:70]}" for g in gaps[:3])

    msg = (
        f"{status} *QA Pipeline - Phase 9*\n\n"
        f"*Feature:* `{state.get('feature', 'N/A')}`\n"
        f"*Run ID:* `{state.get('run_id', 'N/A')}`\n\n"
        f"*Test Cases:* {len(test_cases)}\n"
        f"*Case Review:* {case_review.get('status', 'N/A')}\n"
        f"*Automation Readiness:* {automation_readiness.get('status', 'N/A')}\n"
        f"*Exports:* {len(testcase_exports)}\n"
        f"*Files Generated:* {len(generated_files)}\n"
        f"*Failures:* {len(failures)}\n"
        f"*Coverage:* {coverage:.0f}%\n"
    )
    if state.get("error"):
        msg += f"\n*Error:* `{_error_message(state['error'])}`\n"
    if case_review:
        msg += (
            "\n*AI Case Review:*\n"
            f"  - Score: `{case_review.get('quality_score', 'N/A')}`\n"
            f"  - Critical: `{case_review.get('findings', {}).get('critical', 'N/A')}`\n"
            f"  - Major: `{case_review.get('findings', {}).get('major', 'N/A')}`\n"
        )
    if state.get("testcase_exports"):
        export_lines = "\n".join(
            f"  - {name}: `{path}`"
            for name, path in testcase_exports.items()
        )
        msg += f"\n*Test Case Exports:*\n{export_lines}\n"
    if automation_readiness.get("missing_evidence"):
        missing_lines = "\n".join(
            f"  - {item.get('platform')}/{item.get('type')}: `{item.get('message')}`"
            for item in automation_readiness["missing_evidence"][:5]
        )
        msg += f"\n*Automation Missing Evidence:*\n{missing_lines}\n"
    if bug_lines:
        msg += f"\n*Bugs Found:*\n{bug_lines}\n"
    if gap_lines:
        msg += f"\n*Coverage Gaps:*\n{gap_lines}\n"
    if state.get("gap_report_path"):
        msg += f"\n*Gap Report:* `{state['gap_report_path']}`"

    if token and chat_id:
        try:
            httpx.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
                timeout=10,
            )
            logger.info("telegram_sent", status=status)
        except Exception as e:
            logger.error("telegram_failed", error=str(e))

    # Post QA summary to GitHub PR if PR number is in state
    pr_number = state.get("github_pr_number")
    if pr_number:
        try:
            from mcp_tools.github_client import github_client as gh
            gh.post_qa_summary(
                pr_number=int(pr_number),
                passed=len(test_cases) - len(failures),
                failed=len(failures),
                coverage_pct=coverage,
                suite_lines=[f"{state.get('feature', '')} — {len(test_cases)} scenarios"],
                run_url=os.getenv("GITHUB_RUN_URL", ""),
            )
            logger.info("github_pr_comment_sent", pr=pr_number)
        except Exception as e:
            logger.error("github_pr_comment_failed", error=str(e))

    notifications = [
        *(state.get("notifications") or []),
        {"channel": "qa_ops", "status": status, "sent": bool(token and chat_id)},
    ]
    return {**state, "current_phase": "report", "notifications": notifications}


# ── Routing functions ───────────────────────────────────────────────────────
def route_after_source_intake(state: AgentState) -> Literal["requirements", "report"]:
    error = state.get("error") or {}
    if error.get("phase") == "source_intake":
        return "report"
    return "requirements"


def route_after_case_review(state: AgentState) -> Literal["approval_gate", "report"]:
    review = state.get("case_review") or {}
    if review.get("status") == "passed" and not state.get("error"):
        return "approval_gate"
    return "report"


def route_after_approval(state: AgentState) -> Literal["testcase_export", "report"]:
    if state.get("approved"):
        return "testcase_export"
    if int((state.get("approval") or {}).get("attempt", 0)) >= MAX_APPROVAL_ATTEMPTS:
        return "report"
    return "report"


def route_after_testcase_export(state: AgentState) -> Literal["automation_readiness_gate", "report"]:
    if state.get("testcase_exports") and not state.get("error"):
        return "automation_readiness_gate"
    return "report"


def route_after_automation_readiness(state: AgentState) -> Literal["codegen", "report"]:
    readiness = state.get("automation_readiness") or {}
    if readiness.get("codegen_allowed") and not state.get("error"):
        return "codegen"
    return "report"


def route_after_codegen(state: AgentState) -> Literal["execute", "skill_gap"]:
    if state.get("generated_files"):
        return "execute"
    return "skill_gap"


def route_after_execute(state: AgentState) -> Literal["debug", "skill_gap"]:
    if state.get("failures"):
        return "debug"
    return "skill_gap"


# ── Build graph ─────────────────────────────────────────────────────────────
def build_pipeline():
    from langgraph.graph import END, StateGraph

    graph = StateGraph(AgentState)

    graph.add_node("source_intake", node_source_intake)
    graph.add_node("requirements", node_requirements)
    graph.add_node("testcase", node_testcase)
    graph.add_node("case_review_gate", node_case_review)
    graph.add_node("approval_gate", node_approval)
    graph.add_node("testcase_export", node_testcase_export)
    graph.add_node("automation_readiness_gate", node_automation_readiness)
    graph.add_node("codegen", node_codegen)
    graph.add_node("execute", node_execute)
    graph.add_node("debug", node_debug)
    graph.add_node("skill_gap", node_skill_gap)
    graph.add_node("report", node_report)

    graph.set_entry_point("source_intake")
    graph.add_conditional_edges("source_intake", route_after_source_intake)
    graph.add_edge("requirements", "testcase")
    graph.add_edge("testcase", "case_review_gate")
    graph.add_conditional_edges("case_review_gate", route_after_case_review)
    graph.add_conditional_edges("approval_gate", route_after_approval)
    graph.add_conditional_edges("testcase_export", route_after_testcase_export)
    graph.add_conditional_edges("automation_readiness_gate", route_after_automation_readiness)
    graph.add_conditional_edges("codegen", route_after_codegen)
    graph.add_conditional_edges("execute", route_after_execute)
    graph.add_edge("debug", "skill_gap")
    graph.add_edge("skill_gap", "report")
    graph.add_edge("report", END)

    return graph.compile()


# ── Public entry point ──────────────────────────────────────────────────────
async def run_pipeline(
    feature: str,
    platforms: list[str] | None = None,
    ticket_id: str | None = None,
    story_text: str | None = None,
    feature_url: str | None = None,
    prd_url: str | None = None,
    include_subtasks: bool = False,
    existing_test_cases: list[dict] | None = None,
    automation_evidence: dict[str, Any] | None = None,
    github_pr_number: int | None = None,
) -> AgentState:
    pipeline = build_pipeline()
    init_state: AgentState = {
        "feature": feature,
        "platforms": platforms or ["web"],
        "ticket_id": ticket_id or "",
        "story_text": story_text or feature,
        "feature_url": feature_url or "",
        "prd_url": prd_url or "",
        "include_subtasks": include_subtasks,
        "existing_test_cases": existing_test_cases or [],
        "automation_evidence": automation_evidence or {},
        "github_pr_number": github_pr_number,
        "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "approved": False,
        "approval": _approval_payload("not_started", attempt=0),
        "error": None,
    }
    logger.info("pipeline_start", feature=feature, platforms=platforms)
    final = await pipeline.ainvoke(init_state)
    logger.info(
        "pipeline_complete",
        coverage=final.get("coverage_percentage"),
        bugs=len(final.get("bug_reports") or []),
    )
    return final
