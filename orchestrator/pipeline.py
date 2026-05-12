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

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import httpx
import structlog

from core.agent_state import AgentState

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


# ── Node: Source Intake ─────────────────────────────────────────────────────
def node_source_intake(state: AgentState) -> AgentState:
    logger.info("node_start", node="source_intake", feature=state.get("feature"))

    story_text = state.get("story_text") or state.get("feature", "")
    ticket_id = state.get("ticket_id") or ""
    feature_url = state.get("feature_url") or ""
    prd_url = state.get("prd_url") or ""
    prd_source: dict[str, Any] = {}
    intake_error: dict[str, Any] | None = None

    source_refs = []
    if ticket_id:
        source_refs.append({"type": "jira", "ref": ticket_id})
    if prd_url:
        source_refs.append({"type": "confluence", "ref": prd_url})
    if story_text:
        source_refs.append({"type": "manual_story", "ref": "story_text"})
    if feature_url:
        source_refs.append({"type": "feature_url", "ref": feature_url})

    if prd_url:
        try:
            from mcp_tools.confluence_client.confluence_client import confluence_client

            page = confluence_client.fetch_page(prd_url)
            story_text = (
                f"Source: {page['source_url']}\n"
                f"Title: {page['title']}\n"
                f"Space: {page['space_key']}\n\n"
                f"{page['body_text']}"
            ).strip()
            prd_source = {
                "type": "confluence",
                "url": prd_url,
                "page_id": page["id"],
                "title": page["title"],
                "space_key": page["space_key"],
                "version": page.get("version"),
                "fetched": True,
            }
        except Exception as e:
            logger.error("confluence_fetch_failed", prd_url=prd_url, error=str(e))
            has_manual_fallback = bool(story_text.strip()) and story_text.strip() != state.get("feature", "")
            prd_source = {
                "type": "confluence",
                "url": prd_url,
                "fetched": False,
                "error": str(e),
            }
            if not has_manual_fallback:
                intake_error = {
                    "phase": "source_intake",
                    "message": f"Could not fetch Confluence PRD: {e}",
                }

    source_bundle = {
        "feature": state.get("feature", ""),
        "platforms": state.get("platforms") or ["web"],
        "ticket_id": ticket_id,
        "prd_url": prd_url,
        "prd_content": story_text,
        "prd_source": prd_source,
        "feature_url": feature_url,
        "existing_test_cases": state.get("existing_test_cases") or [],
        "source_refs": source_refs,
        "intake_quality": {
            "has_ticket": bool(ticket_id),
            "has_prd_content": bool(story_text.strip()),
            "has_prd_url": bool(prd_url),
            "prd_fetched": bool(prd_source.get("fetched")),
            "has_feature_url": bool(feature_url),
        },
    }

    return {
        **state,
        "current_phase": "source_intake",
        "source_bundle": source_bundle,
        "story_text": story_text,
        "error": intake_error,
    }


# ── Node: Requirements ───────────────────────────────────────────────────────
def node_requirements(state: AgentState) -> AgentState:
    logger.info("node_start", node="requirements", ticket=state.get("ticket_id"))

    try:
        from agents.requirements_agent import requirements_agent

        source_bundle = state.get("source_bundle") or {}
        if state.get("ticket_id"):
            result = requirements_agent.run_from_jira(state["ticket_id"])
        else:
            result = requirements_agent.run_from_text(
                feature=state.get("feature", ""),
                story_text=source_bundle.get("prd_content") or state.get("story_text", ""),
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
        )
        output = await test_case_agent.run(inp, require_approval=False)
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
        report = reviewer_agent.review(
            prd_content=prd_content,
            test_cases_json=test_cases,
            feature=state.get("feature", "Feature"),
        )

        review = {
            "status": "passed",
            "quality_score": report.overall_quality_score,
            "coverage_percentage": report.coverage_percentage,
            "findings": {
                "critical": report.findings_critical,
                "major": report.findings_major,
                "minor": report.findings_minor,
            },
            "missing_test_cases": report.missing_test_cases,
            "prd_clarifications": report.prd_clarifications,
            "recommendation": report.recommendation,
            "traceability_matrix": report.traceability_matrix,
        }

        if (
            report.findings_critical > 0
            or report.overall_quality_score < CASE_REVIEW_MIN_SCORE
        ):
            review["status"] = "needs_revision"
            return {
                **state,
                "current_phase": "case_review",
                "case_review": review,
                "error": {
                    "phase": "case_review",
                    "message": (
                        "AI case review did not pass quality gate: "
                        f"score={report.overall_quality_score}, "
                        f"critical={report.findings_critical}"
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

        telegram_bot.set_review_queue(review_queue)
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
        saved = code_generator_agent.run(output, platforms[0])

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
    test_cases = state.get("test_cases") or []
    testcase_exports = state.get("testcase_exports") or {}
    generated_files = state.get("generated_files") or {}
    coverage = state.get("coverage_percentage", 0.0)
    status = "PASSED" if not failures and not state.get("error") else "FAILED"

    bug_lines = "\n".join(f"  - [{b['severity']}] {b['title'][:60]}" for b in bugs[:5])
    gap_lines = "\n".join(f"  - {g[:70]}" for g in gaps[:3])

    msg = (
        f"{status} *QA Pipeline - Phase 9*\n\n"
        f"*Feature:* `{state.get('feature', 'N/A')}`\n"
        f"*Run ID:* `{state.get('run_id', 'N/A')}`\n\n"
        f"*Test Cases:* {len(test_cases)}\n"
        f"*Case Review:* {case_review.get('status', 'N/A')}\n"
        f"*Exports:* {len(testcase_exports)}\n"
        f"*Files Generated:* {len(generated_files)}\n"
        f"*Failures:* {len(failures)}\n"
        f"*Coverage:* {coverage:.0f}%\n"
    )
    if state.get("error"):
        msg += f"\n*Error:* `{state['error'].get('message', state['error'])}`\n"
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


def route_after_testcase_export(state: AgentState) -> Literal["codegen", "report"]:
    if state.get("testcase_exports") and not state.get("error"):
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
    existing_test_cases: list[dict] | None = None,
) -> AgentState:
    pipeline = build_pipeline()
    init_state: AgentState = {
        "feature": feature,
        "platforms": platforms or ["web"],
        "ticket_id": ticket_id or "",
        "story_text": story_text or feature,
        "feature_url": feature_url or "",
        "prd_url": prd_url or "",
        "existing_test_cases": existing_test_cases or [],
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
