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
import time
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
    paths: list[str] = []
    if isinstance(generated_files, dict):
        candidates = [str(path) for path in generated_files.values()]
    elif isinstance(generated_files, list):
        candidates = [str(path) for path in generated_files]
    else:
        candidates = []

    seen: set[str] = set()
    for path in candidates:
        if path not in seen:
            paths.append(path)
            seen.add(path)
    return paths


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
    from core.artifacts.artifact_writer import get_run_dir

    feature_slug = _slugify(state.get("feature", "feature"))
    run_id = state.get("run_id") or datetime.now().strftime("%Y%m%d_%H%M%S")

    # Run-scoped dir (canonical)
    review_dir = get_run_dir(run_id, "review")
    base = review_dir / f"test_plan_{feature_slug}_{run_id}_needs_revision"

    # Keep legacy path for backward compat
    legacy_dir = Path("reports/drafts")
    legacy_dir.mkdir(parents=True, exist_ok=True)
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


# ── Node: Test Plan ──────────────────────────────────────────────────────────
def node_test_plan(state: AgentState) -> AgentState:
    from agents.test_plan_agent import test_plan_agent

    logger.info("node_start", node="test_plan", feature=state.get("feature"))

    try:
        requirements = {
            "feature_name":        state.get("feature", ""),
            "ticket_id":           state.get("ticket_id", ""),
            "acceptance_criteria": state.get("acceptance_criteria", []),
            "description":         state.get("story_text", ""),
            "platforms":           state.get("platforms", ["web"]),
        }
        output  = test_plan_agent.create_test_plan(requirements)
        run_id  = state.get("run_id") or datetime.now().strftime("%Y%m%d_%H%M%S")
        test_plan_agent.save_report(output, _slugify(state.get("feature", "feature")), run_id)

        return {
            **state,
            "current_phase": "test_plan",
            "test_plan":      output.model_dump(mode="json"),
            "techniques_used": output.techniques_used,
            "error":          None,
        }
    except Exception as e:
        logger.error("node_failed", node="test_plan", error=str(e))
        return {
            **state,
            "current_phase": "test_plan",
            "error": {"phase": "test_plan", "message": str(e)},
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

        confidence_score = round(report.coverage_percentage / 100.0, 4)

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
                "confidence_score": confidence_score,
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
            "confidence_score": confidence_score,
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
    3-tier confidence-based approval gate (non-blocking).

    Tier 1 — Auto-approve: confidence ≥ AUTO_APPROVE_THRESHOLD AND regression,
              OR APPROVAL_MODE="never".
    Tier 2 — Async Telegram: confidence in [AUTO_REJECT_THRESHOLD, AUTO_APPROVE_THRESHOLD),
              OR APPROVAL_MODE="always". Pipeline ends immediately ("pending"); resumes
              when QA Lead responds via Telegram button or cli.py approve.
    Tier 3 — Auto-reject: confidence < AUTO_REJECT_THRESHOLD (smart mode).
              Re-runs node_testcase with feedback; escalates after 3 retries.
    """
    from config.settings import settings
    from core.telegram_bot import telegram_bot
    from core.workflows.pending_approvals import PendingApprovalStore

    logger.info("node_start", node="approval")

    confidence   = float(state.get("confidence_score") or 0.0)
    is_regression = (state.get("test_type") == "regression")
    mode         = settings.approval_mode
    retry_count  = int(state.get("approval_retry_count") or 0)

    # Guard: nothing to approve
    if not state.get("test_cases") or state.get("testcase_output") is None:
        return {
            **state,
            "current_phase": "approval",
            "approval_decision": "reject",
            "approval_method": "auto",
            "error": {"phase": "approval", "message": "No test cases were generated."},
        }

    # ── Tier 1 — Auto-approve ─────────────────────────────────────────
    if mode == "never" or (
        mode == "smart"
        and confidence >= settings.auto_approve_threshold
        and is_regression
    ):
        logger.info(
            "approval_auto_approved",
            confidence=confidence,
            is_regression=is_regression,
            mode=mode,
        )
        return {
            **state,
            "current_phase": "approval",
            "approved": True,
            "approval_decision": "approve",
            "approval_method": "auto",
            "error": None,
        }

    # ── Tier 3 — Auto-reject ──────────────────────────────────────────
    if mode == "smart" and confidence < settings.auto_reject_threshold:
        if retry_count >= 3:
            logger.warning(
                "approval_max_retries_escalating",
                confidence=confidence,
                retries=retry_count,
            )
            try:
                await telegram_bot.send_alert(
                    f"⚠️ Auto-reject max retries reached for "
                    f"`{state.get('feature', 'unknown')}`\n"
                    f"Confidence: {confidence:.0%} after {retry_count} attempts\n"
                    f"Manual intervention required."
                )
            except Exception as e:
                logger.warning("escalation_notify_failed", error=str(e))
            return {
                **state,
                "current_phase": "approval",
                "approved": False,
                "approval_decision": "escalated",
                "approval_method": "auto",
                "error": None,
            }

        logger.warning(
            "approval_auto_rejected",
            confidence=confidence,
            retry=retry_count + 1,
        )
        return {
            **state,
            "current_phase": "approval",
            "approved": False,
            "approval_decision": "reject",
            "approval_method": "auto",
            "approval_retry_count": retry_count + 1,
            "rejection_feedback": (
                f"Low confidence {confidence:.0%} — re-generating test cases. "
                f"Attempt {retry_count + 1}/3."
            ),
            "error": None,
        }

    # ── Tier 2 — Async Telegram (non-blocking) ────────────────────────
    store       = PendingApprovalStore()
    approval_id = f"{state.get('ticket_id', 'unknown')}_{int(time.time())}"

    store.save(
        approval_id=approval_id,
        state=state,
        expires_hours=settings.approval_timeout_hours,
    )

    output = state.get("testcase_output")
    scenarios_count = len(state.get("test_cases") or [])
    coverage_text = (
        output.coverage_summary
        if hasattr(output, "coverage_summary") and output.coverage_summary
        else str(state.get("case_review", {}).get("coverage_percentage", "N/A"))
    )

    try:
        await telegram_bot.request_approval_async(
            approval_id=approval_id,
            feature=state.get("feature", ""),
            ticket=state.get("ticket_id", ""),
            confidence=confidence,
            scenarios_count=scenarios_count,
            coverage=coverage_text,
            timeout_hours=settings.approval_timeout_hours,
        )
    except Exception as e:
        logger.warning("async_approval_notify_failed", error=str(e))

    logger.info(
        "approval_pending_async",
        approval_id=approval_id,
        confidence=confidence,
        timeout_hours=settings.approval_timeout_hours,
    )

    # Pipeline ends here — resumes when QA Lead responds via Telegram or CLI
    return {
        **state,
        "current_phase": "approval_pending",
        "approved": False,
        "approval_id": approval_id,
        "approval_decision": "pending",
        "approval_method": "async_telegram",
        "error": None,
    }


# ── Node: Test Case Export ──────────────────────────────────────────────────
def node_testcase_export(state: AgentState) -> AgentState:
    from core.agent_contracts import TestCaseAgentOutput
    from core.artifacts.artifact_writer import get_run_dir, write_json
    from skills.reporting.excel_writer import ExcelWriter

    logger.info("node_start", node="testcase_export", feature=state.get("feature"))

    try:
        output = state.get("testcase_output")
        if output is None:
            raise ValueError("Missing approved testcase_output in pipeline state.")
        if isinstance(output, dict):
            output = TestCaseAgentOutput.model_validate(output)

        run_id = state.get("run_id") or datetime.now().strftime("%Y%m%d_%H%M%S")
        tc_dir = get_run_dir(run_id, "test_cases")

        writer = ExcelWriter(output_dir=str(tc_dir))
        paths  = writer.write_both(output)
        exports = {name: str(path) for name, path in paths.items()}

        # Write canonical JSON artifact
        tc_json = tc_dir / "test_cases.json"
        write_json(tc_json, {
            "feature":    output.feature,
            "run_id":     run_id,
            "generated_at": output.generated_at.isoformat(),
            "model_used":   output.model_used,
            "total_scenarios": output.total_scenarios,
            "scenarios":  [s.model_dump(mode="json") for s in output.scenarios],
        })
        exports["json"] = str(tc_json)

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
        saved: dict[str, str] = {}
        for platform in platforms:
            platform_saved = code_generator_agent.run(
                output,
                platform,
                automation_evidence=state.get("automation_evidence") or {},
            )
            for name, path in platform_saved.items():
                key = name if len(platforms) == 1 else f"{platform.value}:{name}"
                saved[key] = path

        # Isolate AI-generated code on a feature branch so it cannot land on main
        # without a human review PR — do this best-effort, never fail the pipeline
        ticket_id = state.get("ticket_id") or "unknown"
        branch_name = f"feature/ai-gen-{ticket_id}"
        try:
            import subprocess as _sp
            _sp.run(["git", "checkout", "-b", branch_name], capture_output=True)
            logger.info("codegen_branch_created", branch=branch_name)
        except Exception as _e:
            logger.warning("codegen_branch_skipped", branch=branch_name, reason=str(_e))

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

    project_root = Path(__file__).resolve().parent.parent

    for fpath in files:
        path = Path(fpath).resolve()

        # Security: reject paths outside the project root (path traversal guard)
        try:
            path.relative_to(project_root)
        except ValueError:
            logger.error("execute_path_traversal_blocked", path=str(path))
            failures.append({
                "test_file": fpath,
                "error_message": f"Blocked: path '{fpath}' is outside project root.",
                "platform": (state.get("platforms") or ["web"])[0],
                "test_name": Path(fpath).stem,
                "location": fpath,
            })
            continue

        if not path.exists():
            failures.append({
                "test_file": str(path),
                "error_message": "Generated test file does not exist.",
                "platform": (state.get("platforms") or ["web"])[0],
                "test_name": path.stem,
                "location": str(path),
            })
            continue

        report_path = Path("reports") / f"pytest_{path.stem}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        run = subprocess.run(
            [
                PYTHON_BIN,
                "-m",
                "pytest",
                str(path),
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
        results[str(path)] = {
            "passed": passed,
            "stdout": run.stdout[-4000:],
            "stderr": run.stderr[-4000:],
            "returncode": run.returncode,
            "json_report": str(report_path),
        }
        if not passed:
            failures.append({
                "test_file": str(path),
                "error_message": (run.stdout + "\n" + run.stderr)[-1000:],
                "platform": (state.get("platforms") or ["web"])[0],
                "test_name": path.stem,
                "location": str(path),
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
    from core.artifacts.artifact_writer import get_run_dir, write_json

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
            "title":                 report.title,
            "severity":              report.severity,
            "bug_type":              report.bug_type,
            "failure_classification": report.failure_classification,
            "recommended_action":    report.recommended_action,
            "confidence":            report.confidence,
            "auto_fix_allowed":      report.auto_fix_allowed,
            "root_cause":            report.root_cause,
            "steps":                 report.steps_to_reproduce,
            "expected_behavior":     report.expected_behavior,
            "actual_behavior":       report.actual_behavior,
            "affected_component":    report.affected_component,
            "suggested_fix":         report.suggested_fix,
            "integrity_notes":       report.integrity_notes,
            "jira_key":              report.jira_key,
            "needs_dev_attention":   report.needs_dev_attention,
            "labels":                report.labels,
        })

    # Write run-scoped debug artifact
    run_id = state.get("run_id") or datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_dir = get_run_dir(run_id, "debug")
    write_json(debug_dir / "debug_report.json", {
        "run_id":      run_id,
        "feature":     state.get("feature"),
        "timestamp":   datetime.now().isoformat(),
        "bug_reports": bug_reports,
    })

    return {**state, "current_phase": "debug", "bug_reports": bug_reports}


# ── Node: Flaky Analysis ────────────────────────────────────────────────────
def node_flaky_analysis(state: AgentState) -> AgentState:
    """
    Record current run outcomes then run FlakyTestAgent across history.
    Only tests with ≥3 historical runs and mixed outcomes are classified.
    Product bugs are never quarantined — integrity is preserved by the agent.
    """
    import csv as _csv
    from agents.flaky_test_agent import flaky_test_agent
    from core.artifacts.artifact_writer import get_run_dir, write_json
    from core.flaky_history import get_history, record_run

    logger.info("node_start", node="flaky_analysis")

    run_id     = state.get("run_id") or datetime.now().strftime("%Y%m%d_%H%M%S")
    exec_results = state.get("execution_results") or {}

    # Persist this run's outcomes before analyzing
    if exec_results:
        try:
            record_run(exec_results)
        except Exception as e:
            logger.warning("flaky_history_record_failed", error=str(e))

    # Analyze full history for flaky candidates
    flaky_results: list[dict] = []
    try:
        history  = get_history()
        analyzed = flaky_test_agent.analyze_batch(history, flakiness_threshold=0.20)
        flaky_results = [
            {
                "test_name":              r.test_name,
                "flakiness_score":        r.flakiness_score,
                "failure_count":          r.failure_count,
                "total_runs":             r.total_runs,
                "category":               r.category,
                "confidence":             r.confidence,
                "root_cause":             r.root_cause,
                "remediation":            r.remediation,
                "quarantine_recommended": r.quarantine_recommended,
                "error_patterns":         r.error_patterns[:3],
            }
            for r in analyzed
        ]
    except Exception as e:
        logger.error("flaky_analysis_failed", error=str(e))

    # Write run-scoped artifacts
    try:
        flaky_dir = get_run_dir(run_id, "flaky")
        write_json(flaky_dir / "flaky_report.json", {
            "run_id":        run_id,
            "feature":       state.get("feature"),
            "timestamp":     datetime.now().isoformat(),
            "flaky_tests":   flaky_results,
            "total_analyzed": len(get_history()),
        })

        csv_path = flaky_dir / "flaky_report.csv"
        if flaky_results:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                fieldnames = [
                    "test_name", "flakiness_score", "failure_count", "total_runs",
                    "category", "confidence", "quarantine_recommended", "root_cause",
                ]
                writer = _csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in flaky_results:
                    writer.writerow({k: r.get(k, "") for k in fieldnames})
            logger.info("flaky_csv_written", path=str(csv_path), count=len(flaky_results))
    except Exception as e:
        logger.warning("flaky_artifact_write_failed", error=str(e))

    logger.info("flaky_analysis_complete", candidates=len(flaky_results))
    return {
        **state,
        "current_phase": "flaky_analysis",
        "flaky_results": flaky_results,
    }


# ── Node: Skill Gap Analysis ────────────────────────────────────────────────
def node_skill_gap(state: AgentState) -> AgentState:
    from agents.skill_gap_agent import skill_gap_agent
    from core.artifacts.artifact_writer import get_run_dir, write_json, write_markdown

    logger.info("node_start", node="skill_gap")

    run_id  = state.get("run_id") or datetime.now().strftime("%Y%m%d_%H%M%S")
    feature = state.get("feature", "unknown")

    gap = skill_gap_agent.analyze(
        acceptance_criteria=state.get("acceptance_criteria", []),
        test_cases=state.get("test_cases", []),
        feature=feature,
    )

    # Write to run-scoped dir (canonical) + legacy path (backward compat)
    sg_dir    = get_run_dir(run_id, "skill_gap")
    json_path = sg_dir / "skill_gap_report.json"
    write_json(json_path, {"feature": feature, "run_id": run_id, **gap})

    # Markdown summary
    missing   = gap.get("missing_scenarios", [])
    gaps_md   = "\n".join(f"- {g}" for g in missing[:20]) or "_None identified_"
    recs_md   = "\n".join(f"- {r}" for r in gap.get("recommendations", [])[:10]) or "_None_"
    md_content = (
        f"# Skill Gap Report — {feature}\n\n"
        f"**Coverage:** {gap.get('coverage_percentage', 0):.1f}%  "
        f"| **Run ID:** `{run_id}`\n\n"
        f"## Missing Scenarios\n\n{gaps_md}\n\n"
        f"## Recommendations\n\n{recs_md}\n"
    )
    write_markdown(sg_dir / "skill_gap_summary.md", md_content)

    # Legacy path for CLI backward compat
    legacy_path = skill_gap_agent.save_report(gap_data=gap, feature=feature, run_id=run_id)

    coverage_report = {**gap, "report_path": str(json_path)}
    return {
        **state,
        "current_phase":      "skill_gap",
        "coverage_report":    coverage_report,
        "coverage_gaps":      gap.get("missing_scenarios", []),
        "coverage_percentage": gap.get("coverage_percentage", 0.0),
        "gap_report_path":    str(json_path),
    }


# ── Node: Jira Update ───────────────────────────────────────────────────────
def node_jira_update(state: AgentState) -> AgentState:
    """Transition Jira ticket status after test execution completes."""
    ticket_id = state.get("ticket_id")
    if not ticket_id:
        logger.info("jira_update_skipped", reason="no ticket_id")
        return state

    failures = state.get("failures") or []

    try:
        from integrations.jira_client.jira_client import jira_client

        if not failures:
            ok = jira_client.transition_issue(ticket_id, "DONE")
            if ok:
                logger.info("jira_transitioned", ticket=ticket_id, status="DONE")
            else:
                logger.warning("jira_transition_failed", ticket=ticket_id, status="DONE")
        else:
            ok = jira_client.transition_issue(ticket_id, "IN TEST")
            if ok:
                logger.info("jira_transitioned", ticket=ticket_id, status="IN TEST")
            else:
                logger.warning("jira_transition_failed", ticket=ticket_id, status="IN TEST")

            comment = (
                f"QA Pipeline completed with {len(failures)} failure(s).\n"
                f"Run ID: {state.get('run_id', 'N/A')}\n"
                f"Feature: {state.get('feature', 'N/A')}"
            )
            jira_client.add_comment(ticket_id, comment)
    except Exception as e:
        logger.warning("jira_update_failed", ticket=ticket_id, error=str(e))

    return state


# ── Node: Report ────────────────────────────────────────────────────────────
def node_report(state: AgentState) -> AgentState:
    """Send final Telegram summary report."""
    from core.source_intake.security import redact_internal_text
    from config.settings import settings as _settings

    logger.info("node_start", node="report")

    token = _settings.telegram_bot_token
    chat_id = _settings.telegram_qa_ops_chat_id

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

    bug_lines = "\n".join(
        f"  - [{b['severity']}] {redact_internal_text(b['title'][:60]).text}"
        for b in bugs[:5]
    )
    gap_lines = "\n".join(
        f"  - {redact_internal_text(g[:70]).text}" for g in gaps[:3]
    )

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
        safe_err = redact_internal_text(_error_message(state["error"])[:200]).text
        msg += f"\n*Error:* `{safe_err}`\n"
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
            from integrations.github_client import github_client as gh
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

    # Write final summary artifact to run-scoped dir
    run_id = state.get("run_id") or datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        from core.artifacts.artifact_writer import write_final_summary
        write_final_summary(run_id, state)
    except Exception as e:
        logger.warning("final_summary_write_failed", error=str(e))

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


def route_after_approval(state: AgentState) -> str:
    from langgraph.graph import END

    decision = state.get("approval_decision")
    if decision == "approve":
        return "testcase_export"
    if decision == "reject":
        return "testcase"   # re-generate with rejection_feedback in state
    # "pending", "escalated", or unset — stop the pipeline run
    return END


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


def route_after_execute(state: AgentState) -> Literal["debug", "flaky_analysis"]:
    if state.get("failures"):
        return "debug"
    # No failures — skip debug but still record history and run skill_gap
    return "flaky_analysis"


# ── Build graph ─────────────────────────────────────────────────────────────
def build_pipeline():
    from pathlib import Path as _Path

    from langgraph.graph import END, StateGraph
    from langgraph.checkpoint.memory import MemorySaver

    graph = StateGraph(AgentState)

    graph.add_node("source_intake", node_source_intake)
    graph.add_node("requirements", node_requirements)
    graph.add_node("test_plan", node_test_plan)
    graph.add_node("testcase", node_testcase)
    graph.add_node("case_review_gate", node_case_review)
    graph.add_node("approval_gate", node_approval)
    graph.add_node("testcase_export", node_testcase_export)
    graph.add_node("automation_readiness_gate", node_automation_readiness)
    graph.add_node("codegen", node_codegen)
    graph.add_node("execute", node_execute)
    graph.add_node("debug", node_debug)
    graph.add_node("flaky_analysis", node_flaky_analysis)
    graph.add_node("skill_gap", node_skill_gap)
    graph.add_node("report", node_report)
    graph.add_node("jira_update", node_jira_update)

    graph.set_entry_point("source_intake")
    graph.add_conditional_edges("source_intake", route_after_source_intake)
    graph.add_edge("requirements", "test_plan")
    graph.add_edge("test_plan", "testcase")
    graph.add_edge("testcase", "case_review_gate")
    graph.add_conditional_edges("case_review_gate", route_after_case_review)
    graph.add_conditional_edges("approval_gate", route_after_approval)
    graph.add_conditional_edges("testcase_export", route_after_testcase_export)
    graph.add_conditional_edges("automation_readiness_gate", route_after_automation_readiness)
    graph.add_conditional_edges("codegen", route_after_codegen)
    graph.add_conditional_edges("execute", route_after_execute)
    graph.add_edge("debug", "flaky_analysis")
    graph.add_edge("flaky_analysis", "skill_gap")
    graph.add_edge("skill_gap", "report")
    graph.add_edge("report", "jira_update")
    graph.add_edge("jira_update", END)

    # ── Checkpointer: enables pipeline resumability on crash ─────────────
    try:
        from config.settings import settings as _settings
        use_persistent = _settings.use_persistent_checkpointer
    except Exception:
        use_persistent = False

    if use_persistent:
        import sqlite3
        import uuid
        from langgraph.checkpoint.sqlite import SqliteSaver
        # Per-run DB path prevents concurrent-writer lock contention across webhook pipelines
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
        db_path = _Path(f"checkpoints/pipeline_{run_id}.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        checkpointer = SqliteSaver(conn)
        logger.info("pipeline_checkpointer", type="sqlite", path=str(db_path))
    else:
        checkpointer = MemorySaver()
        logger.info("pipeline_checkpointer", type="memory")

    return graph.compile(checkpointer=checkpointer)


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
