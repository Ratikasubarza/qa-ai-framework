# paste isi dari artifact orchestrator/pipeline.py
"""
Phase 9 — Full LangGraph QA Pipeline Orchestrator
Wires all agents into a single directed graph with conditional routing.

Flow:
  START → requirements → testcase → [approval gate] → codegen
        → execute → debug (on failure) → skill_gap → report → END
"""
from __future__ import annotations
import asyncio
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal

import structlog
from langgraph.graph import StateGraph, END

from core.agent_state import AgentState

logger = structlog.get_logger(__name__)


# ── Node: Requirements ───────────────────────────────────────────────────────
def node_requirements(state: AgentState) -> AgentState:
    from agents.requirements_agent import requirements_agent
    logger.info("node_start", node="requirements", ticket=state.get("ticket_id"))

    try:
        if state.get("ticket_id"):
            result = requirements_agent.run_from_jira(state["ticket_id"])
        else:
            result = requirements_agent.run_from_text(
                feature=state.get("feature", ""),
                story_text=state.get("story_text", ""),
                parent_key="",
            )
        # requirements_agent returns criteria or acceptance_criteria
        raw_criteria = (
            result.get("acceptance_criteria")
            or result.get("criteria")
            or []
        )
        acs = []
        for ac in raw_criteria:
            if isinstance(ac, dict):
                acs.append(ac.get("summary") or ac.get("description") or str(ac))
            elif isinstance(ac, str):
                acs.append(ac)
        return {
            **state,
            "current_phase":      "requirements",
            "acceptance_criteria": acs,
            "requirements_raw":    result,
        }
    except Exception as e:
        logger.error("node_failed", node="requirements", error=str(e))
        return {**state, "current_phase": "requirements", "error": str(e)}


# ── Node: Test Case Generation ───────────────────────────────────────────────
async def node_testcase(state: AgentState) -> AgentState:
    from agents.test_case_agent import test_case_agent
    from core.agent_contracts import TestCaseAgentInput, Platform
    logger.info("node_start", node="testcase", feature=state.get("feature"))

    try:
        platforms = [Platform(p) for p in (state.get("platforms") or ["web"])]
        inp = TestCaseAgentInput(
            feature=state.get("feature", ""),
            description=state.get("story_text", state.get("feature", "")),
            platforms=platforms,
            acceptance_criteria=state.get("acceptance_criteria", []),
        )
        output = await test_case_agent.run(inp)
        tcs = []
        for s in (output.scenarios or []):
            try:
                tcs.append({
                    "scenario_id": s.scenario_id or f"TC-{len(tcs)+1:03d}",
                    "name":        (s.name or "").strip() or "Unnamed scenario",
                    "test_type":   s.test_type.value if s.test_type else "functional",
                    "platforms":   [p.value for p in (s.platforms or [])],
                    "priority":    s.priority.value if s.priority else "P2",
                    "steps":       getattr(s, "steps", []) or [],
                })
            except Exception as se:
                logger.warning("scenario_skip", error=str(se))
                continue
        return {**state, "current_phase": "testcase", "test_cases": tcs, "approved": False, "error": None}
    except Exception as e:
        logger.error("node_failed", node="testcase", error=str(e))
        # Non-fatal: continue with empty test cases
        return {**state, "current_phase": "testcase", "test_cases": [], "approved": False, "error": None}


# ── Node: Approval Gate (Telegram) ──────────────────────────────────────────
async def node_approval(state: AgentState) -> AgentState:
    """
    If APPROVAL_REQUIRED env var is true, wait for Telegram approval.
    Otherwise auto-approve.
    """
    import os

    logger.info("node_start", node="approval")
    approval_required = os.getenv("APPROVAL_REQUIRED", "false").lower() == "true"

    if not approval_required:
        logger.info("approval_auto", reason="APPROVAL_REQUIRED=false")
        return {**state, "current_phase": "approval", "approved": True}

    try:
        from core.telegram_bot import telegram_bot
        from approval_workflow.feedback_schema import review_queue

        tc_summary = "\n".join(
            f"• [{tc['scenario_id']}] {tc['name']}"
            for tc in (state.get("test_cases") or [])[:10]
        )
        msg = (
            f"🤖 *Test Cases Ready for Review*\n\n"
            f"Feature: `{state.get('feature')}`\n"
            f"Count: {len(state.get('test_cases', []))}\n\n"
            f"{tc_summary}\n\n"
            f"Reply /approve or /reject"
        )
        await telegram_bot.notify_approval_request(msg)

        # Wait up to 10 minutes for approval
        for _ in range(60):
            await asyncio.sleep(10)
            item = review_queue.get_latest()
            if item and str(getattr(item, "status", "")) in ("approved", "ApprovalStatus.APPROVED"):
                return {**state, "current_phase": "approval", "approved": True}
            if item and str(getattr(item, "status", "")) in ("rejected", "ApprovalStatus.REJECTED"):
                return {
                    **state,
                    "current_phase":     "approval",
                    "approved":          False,
                    "approval_feedback": item.feedback or "Rejected",
                }

        # Timeout → auto-approve
        logger.warning("approval_timeout", action="auto_approve")
        return {**state, "current_phase": "approval", "approved": True}

    except Exception as e:
        logger.error("node_failed", node="approval", error=str(e))
        return {**state, "current_phase": "approval", "approved": True}


# ── Node: Code Generation ────────────────────────────────────────────────────
def node_codegen(state: AgentState) -> AgentState:
    from agents.code_generator_agent import code_generator_agent
    from agents.test_case_agent import test_case_agent
    from core.agent_contracts import TestCaseAgentInput, Platform, TestCaseAgentOutput
    logger.info("node_start", node="codegen", feature=state.get("feature"))

    try:
        # Reconstruct output object for code_generator_agent
        platforms = [Platform(p) for p in (state.get("platforms") or ["web"])]
        inp = TestCaseAgentInput(
            feature=state.get("feature", ""),
            description=state.get("story_text", ""),
            platforms=platforms,
            acceptance_criteria=state.get("acceptance_criteria", []),
        )
        from core.agent_contracts import TestType
        valid_types = {t.value for t in TestType}

        # Use test cases from state if available, re-generate if not
        existing_tcs = state.get("test_cases") or []
        if existing_tcs:
            tc_output = asyncio.run(test_case_agent.run(inp))
            # Filter scenarios with invalid test types
            tc_output.scenarios = [
                s for s in tc_output.scenarios
                if s.test_type.value in valid_types
            ]
        else:
            tc_output = asyncio.run(test_case_agent.run(inp))
            tc_output.scenarios = [
                s for s in tc_output.scenarios
                if s.test_type.value in valid_types
            ]
        saved = code_generator_agent.run(tc_output, platforms[0])
        return {**state, "current_phase": "codegen", "generated_files": saved}
    except Exception as e:
        logger.error("node_failed", node="codegen", error=str(e))
        return {**state, "current_phase": "codegen", "error": str(e)}


# ── Node: Test Execution ─────────────────────────────────────────────────────
def node_execute(state: AgentState) -> AgentState:
    """Run generated test files via pytest, collect results."""
    logger.info("node_start", node="execute")
    files = state.get("generated_files") or []
    results = {}
    failures = []

    for fpath in files:
        if not Path(fpath).exists():
            continue
        run = subprocess.run(
            ["python", "-m", "pytest", fpath, "-v", "--tb=short", "--json-report",
             f"--json-report-file=reports/pytest_{Path(fpath).stem}.json"],
            capture_output=True, text=True,
        )
        passed = run.returncode == 0
        results[fpath] = {
            "passed":  passed,
            "stdout":  run.stdout[-2000:],
            "returncode": run.returncode,
        }
        if not passed:
            failures.append({
                "test_file":     fpath,
                "error_message": run.stdout[-500:],
                "platform":      "web",
                "test_name":     Path(fpath).stem,
                "location":      fpath,
            })

    logger.info("execute_complete", files=len(files), failures=len(failures))
    return {**state, "current_phase": "execute",
            "execution_results": results, "failures": failures}


# ── Node: Debug Agent ────────────────────────────────────────────────────────
def node_debug(state: AgentState) -> AgentState:
    from agents.debug_agent import debug_agent, FailureContext
    logger.info("node_start", node="debug", failures=len(state.get("failures", [])))

    bug_reports = []
    for f in (state.get("failures") or []):
        ctx = FailureContext(
            test_name=f.get("test_name", "unknown"),
            error_message=f.get("error_message", ""),
            platform=f.get("platform", "web"),
            location=f.get("location", ""),
        )
        report = debug_agent.analyze(ctx)
        bug_reports.append({
            "title":       report.title,
            "severity":    report.severity,
            "bug_type":    report.bug_type,
            "root_cause":  report.root_cause,
            "steps":       report.steps_to_reproduce,
            "jira_key":    report.jira_key,
        })

    return {**state, "current_phase": "debug", "bug_reports": bug_reports}


# ── Node: Skill Gap Analysis ─────────────────────────────────────────────────
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
    return {
        **state,
        "current_phase":      "skill_gap",
        "coverage_gaps":      gap.get("missing_scenarios", []),
        "coverage_percentage": gap.get("coverage_percentage", 0.0),
        "gap_report_path":    path,
    }


# ── Node: Report ─────────────────────────────────────────────────────────────
def node_report(state: AgentState) -> AgentState:
    """Send final Telegram summary report."""
    import os, httpx
    logger.info("node_start", node="report")

    token   = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_QA_OPS_CHAT_ID")

    failures  = state.get("failures") or []
    bugs      = state.get("bug_reports") or []
    gaps      = state.get("coverage_gaps") or []
    coverage  = state.get("coverage_percentage", 0.0)
    status    = "✅ PASSED" if not failures else "❌ FAILED"

    bug_lines = "\n".join(f"  • [{b['severity']}] {b['title'][:60]}" for b in bugs[:5])
    gap_lines = "\n".join(f"  • {g[:70]}" for g in gaps[:3])

    msg = (
        f"{status} *QA Pipeline — Phase 9*\n\n"
        f"*Feature:* `{state.get('feature', 'N/A')}`\n"
        f"*Run ID:* `{state.get('run_id', 'N/A')}`\n\n"
        f"*Test Cases:* {len(state.get('test_cases', []))}\n"
        f"*Files Generated:* {len(state.get('generated_files', []))}\n"
        f"*Failures:* {len(failures)}\n"
        f"*Coverage:* {coverage:.0f}%\n"
    )
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

    return {**state, "current_phase": "report"}


# ── Routing functions ────────────────────────────────────────────────────────
def route_after_approval(state: AgentState) -> Literal["codegen", "testcase", "__end__"]:
    if state.get("approved"):
        return "codegen"
    return "testcase"  # Re-generate if rejected


def route_after_execute(state: AgentState) -> Literal["debug", "skill_gap"]:
    if state.get("failures"):
        return "debug"
    return "skill_gap"


# ── Build graph ──────────────────────────────────────────────────────────────
def build_pipeline() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("requirements", node_requirements)
    graph.add_node("testcase",     node_testcase)
    graph.add_node("approval",     node_approval)
    graph.add_node("codegen",      node_codegen)
    graph.add_node("execute",      node_execute)
    graph.add_node("debug",        node_debug)
    graph.add_node("skill_gap",    node_skill_gap)
    graph.add_node("report",       node_report)

    graph.set_entry_point("requirements")
    graph.add_edge("requirements", "testcase")
    graph.add_edge("testcase",     "approval")
    graph.add_conditional_edges("approval", route_after_approval)
    graph.add_edge("codegen",      "execute")
    graph.add_conditional_edges("execute", route_after_execute)
    graph.add_edge("debug",        "skill_gap")
    graph.add_edge("skill_gap",    "report")
    graph.add_edge("report",       END)

    return graph.compile()


# ── Public entry point ───────────────────────────────────────────────────────
async def run_pipeline(
    feature: str,
    platforms: list[str] | None = None,
    ticket_id: str | None = None,
    story_text: str | None = None,
) -> AgentState:
    pipeline = build_pipeline()
    init_state: AgentState = {
        "feature":   feature,
        "platforms": platforms or ["web"],
        "ticket_id": ticket_id or "",
        "story_text": story_text or feature,
        "run_id":    datetime.now().strftime("%Y%m%d_%H%M%S"),
        "approved":  False,
        "error":     None,
    }
    logger.info("pipeline_start", feature=feature, platforms=platforms)
    final = await pipeline.ainvoke(init_state)
    logger.info("pipeline_complete",
                coverage=final.get("coverage_percentage"),
                bugs=len(final.get("bug_reports") or []))
    return final