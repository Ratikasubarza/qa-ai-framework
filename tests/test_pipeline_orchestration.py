import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

from core.agent_contracts import (
    Platform,
    Priority,
    ScenarioSchema,
    TestCaseAgentOutput as CaseOutput,
    TestStep as Step,
    TestType as CaseType,
)
from orchestrator import pipeline


def _testcase_output() -> CaseOutput:
    return CaseOutput(
        feature="Login",
        scenarios=[
            ScenarioSchema(
                scenario_id="TC-001",
                name="Valid login",
                precondition="User exists",
                steps=[
                    Step(
                        step_number=1,
                        action="Enter valid credentials",
                        expected="Login succeeds",
                    )
                ],
                expected_result="Dashboard opens",
                test_type=CaseType.SMOKE,
                platforms=[Platform.WEB],
                priority=Priority.HIGH,
                edge_cases=["empty password"],
                combination_edge_cases=["valid email with expired session"],
                weird_edge_cases=["rapid double submit"],
            )
        ],
        coverage_summary="ok",
        total_scenarios=1,
        prompt_version="test",
        model_used="fake-model",
    )


def test_source_intake_builds_context_bundle():
    state = pipeline.node_source_intake({
        "feature": "Login",
        "platforms": ["web", "api"],
        "ticket_id": "QA-123",
        "story_text": "Users can log in with email and password.",
        "feature_url": "https://app-dev.thehono.com/login",
        "existing_test_cases": [{"scenario_id": "TC-OLD"}],
    })

    bundle = state["source_bundle"]
    assert bundle["feature"] == "Login"
    assert bundle["platforms"] == ["web", "api"]
    assert bundle["ticket_id"] == "QA-123"
    assert bundle["feature_url"] == "https://app-dev.thehono.com/login"
    assert bundle["existing_test_cases"] == [{"scenario_id": "TC-OLD"}]
    assert bundle["intake_quality"]["has_ticket"] is True
    assert bundle["intake_quality"]["has_prd_content"] is True
    assert bundle["intake_quality"]["has_feature_url"] is True
    assert bundle["intake_quality"]["has_prd_url"] is False
    assert bundle["intake_quality"]["prd_fetched"] is False


def test_source_intake_fetches_confluence_prd(monkeypatch):
    class FakeConfluenceClient:
        def fetch_page(self, prd_url):
            assert prd_url == "https://thehono.atlassian.net/wiki/spaces/H/pages/37847042/PRD"
            return {
                "id": "37847042",
                "title": "PRD - Sprint 3 - Post Management",
                "space_key": "H",
                "source_url": prd_url,
                "body_text": "Users can create and manage posts.",
                "version": 7,
            }

    fake_module = SimpleNamespace(confluence_client=FakeConfluenceClient())
    monkeypatch.setitem(
        sys.modules,
        "mcp_tools.confluence_client.confluence_client",
        fake_module,
    )

    state = pipeline.node_source_intake({
        "feature": "Post Management",
        "platforms": ["android"],
        "story_text": "Post Management",
        "prd_url": "https://thehono.atlassian.net/wiki/spaces/H/pages/37847042/PRD",
    })

    bundle = state["source_bundle"]
    assert state["error"] is None
    assert "Users can create and manage posts." in bundle["prd_content"]
    assert bundle["prd_source"] == {
        "type": "confluence",
        "url": "https://thehono.atlassian.net/wiki/spaces/H/pages/37847042/PRD",
        "page_id": "37847042",
        "title": "PRD - Sprint 3 - Post Management",
        "space_key": "H",
        "version": 7,
        "fetched": True,
    }
    assert bundle["intake_quality"]["prd_fetched"] is True


def test_source_intake_composes_jira_prd_and_subtasks(monkeypatch):
    class FakeJiraClient:
        def get_issue(self, issue_key):
            assert issue_key == "HM-123"
            return {
                "key": "HM-123",
                "summary": "Create post API",
                "status": "In Progress",
                "priority": "High",
                "issue_type": "Story",
                "description": "API allows an authenticated user to create a post.",
                "acceptance_criteria": ["POST /posts creates a visible post."],
                "subtasks": [{
                    "key": "HM-124",
                    "summary": "Implement API contract",
                    "status": "Done",
                    "description": "Payload includes content, audience, and image IDs.",
                }],
            }

    class FakeConfluenceClient:
        def fetch_page(self, prd_url):
            assert prd_url == "https://thehono.atlassian.net/wiki/spaces/H/pages/37847042/PRD"
            return {
                "id": "37847042",
                "title": "PRD - Sprint 3 - Post Management",
                "space_key": "H",
                "source_url": prd_url,
                "body_text": "Post Management product behavior.",
                "version": 7,
            }

    monkeypatch.setitem(
        sys.modules,
        "mcp_tools.jira_client.jira_client",
        SimpleNamespace(jira_client=FakeJiraClient()),
    )
    monkeypatch.setitem(
        sys.modules,
        "mcp_tools.confluence_client.confluence_client",
        SimpleNamespace(confluence_client=FakeConfluenceClient()),
    )

    state = pipeline.node_source_intake({
        "feature": "Post Composer API",
        "platforms": ["api"],
        "ticket_id": "HM-123",
        "story_text": "Check validation for API payload.",
        "prd_url": "https://thehono.atlassian.net/wiki/spaces/H/pages/37847042/PRD",
        "include_subtasks": True,
    })

    bundle = state["source_bundle"]
    assert "=== JIRA STORY / TICKET ===" in bundle["prd_content"]
    assert "=== PRODUCT PRD CONTEXT ===" in bundle["prd_content"]
    assert "=== MANUAL STORY CONTEXT ===" in bundle["prd_content"]
    assert "Implement API contract" in bundle["prd_content"]
    assert "Payload includes content, audience, and image IDs." in bundle["prd_content"]
    assert bundle["jira_source"]["fetched"] is True
    assert bundle["jira_source"]["subtasks_included"] is True
    assert bundle["jira_source"]["subtask_count"] == 1
    assert bundle["jira_source"]["included_subtask_count"] == 1
    assert bundle["intake_quality"]["jira_fetched"] is True
    assert bundle["intake_quality"]["subtasks_included"] is True


def test_source_intake_filters_parent_subtasks_by_platform(monkeypatch):
    class FakeJiraClient:
        def get_issue(self, issue_key):
            assert issue_key == "HM-516"
            return {
                "key": "HM-516",
                "summary": "Profile content tabs",
                "status": "To Do",
                "priority": "Medium",
                "issue_type": "Story",
                "description": "Users can view posts and media tabs.",
                "acceptance_criteria": ["Profile tabs show posts and media."],
                "subtasks": [
                    {
                        "key": "HM-557",
                        "summary": "[BE] Post Visibility API",
                        "status": "Done",
                        "description": "API returns visibility payload.",
                    },
                    {
                        "key": "HM-558",
                        "summary": "[Mobile] Profile Posts Tab - UI",
                        "status": "Done",
                        "description": "Android UI supports posts tab pagination.",
                    },
                    {
                        "key": "HM-559",
                        "summary": "[FE] Profile Posts Tab - UI",
                        "status": "To Do",
                        "description": "Web UI supports posts tab pagination.",
                    },
                ],
            }

    monkeypatch.setitem(
        sys.modules,
        "mcp_tools.jira_client.jira_client",
        SimpleNamespace(jira_client=FakeJiraClient()),
    )

    state = pipeline.node_source_intake({
        "feature": "HM-516 Profile Posts Tab Android",
        "platforms": ["android"],
        "ticket_id": "HM-516",
        "story_text": "Generate Android UI cases only.",
        "include_subtasks": True,
    })

    bundle = state["source_bundle"]
    assert "HM-558: [Mobile] Profile Posts Tab - UI" in bundle["prd_content"]
    assert "HM-557: [BE] Post Visibility API" not in bundle["prd_content"]
    assert "HM-559: [FE] Profile Posts Tab - UI" not in bundle["prd_content"]
    assert bundle["jira_source"]["subtask_count"] == 3
    assert bundle["jira_source"]["included_subtask_count"] == 1
    assert bundle["jira_source"]["subtask_filter_platforms"] == ["android"]


def test_source_intake_blocks_when_prd_url_unreadable_without_manual_fallback(monkeypatch):
    class FakeConfluenceClient:
        def fetch_page(self, prd_url):
            raise PermissionError("Confluence authentication failed with 401.")

    fake_module = SimpleNamespace(confluence_client=FakeConfluenceClient())
    monkeypatch.setitem(
        sys.modules,
        "mcp_tools.confluence_client.confluence_client",
        fake_module,
    )

    state = pipeline.node_source_intake({
        "feature": "Post Management",
        "platforms": ["android"],
        "story_text": "Post Management",
        "prd_url": "https://thehono.atlassian.net/wiki/spaces/H/pages/37847042/PRD",
    })

    assert state["error"]["phase"] == "source_intake"
    assert pipeline.route_after_source_intake(state) == "report"


def test_source_intake_ignores_placeholder_prd_url():
    state = pipeline.node_source_intake({
        "feature": "Post Management",
        "platforms": ["android"],
        "story_text": "Focus only Android Posts tab behavior.",
        "prd_url": "...",
    })

    bundle = state["source_bundle"]
    assert state["error"] is None
    assert bundle["prd_source"] == {}
    assert bundle["intake_quality"]["has_prd_url"] is False
    assert not any(ref["type"] == "confluence" for ref in bundle["source_refs"])


def test_build_pipeline_compiles_without_state_key_node_collisions():
    compiled = pipeline.build_pipeline()
    assert compiled is not None


def test_requirements_uses_normalized_source_bundle_when_jira_was_fetched(monkeypatch):
    calls = []

    class FakeRequirementsAgent:
        def run_from_text(self, feature, story_text, parent_key):
            calls.append(("text", feature, story_text, parent_key))
            return {"criteria": []}

        def run_from_jira(self, ticket_id):
            calls.append(("jira", ticket_id))
            return {"criteria": []}

    monkeypatch.setitem(
        sys.modules,
        "agents.requirements_agent",
        SimpleNamespace(requirements_agent=FakeRequirementsAgent()),
    )

    state = pipeline.node_requirements({
        "feature": "Post Composer API",
        "ticket_id": "HM-123",
        "source_bundle": {
            "prd_content": "Combined Jira, subtask, and PRD context.",
            "jira_source": {"fetched": True},
            "prd_source": {},
        },
    })

    assert state["error"] is None
    assert calls == [(
        "text",
        "Post Composer API",
        "Combined Jira, subtask, and PRD context.",
        "HM-123",
    )]


def test_case_review_quality_gate_passes(monkeypatch):
    calls = []

    class FakeReviewer:
        def review(self, prd_content, test_cases_json, feature, target_platforms=None):
            calls.append((prd_content, test_cases_json, feature, target_platforms))
            return SimpleNamespace(
                overall_quality_score=8.5,
                coverage_percentage=90.0,
                findings_critical=0,
                findings_major=1,
                findings_minor=2,
                detailed_findings=[],
                missing_test_cases=[],
                prd_clarifications=[],
                recommendation="approve",
                traceability_matrix=[],
            )

    fake_module = SimpleNamespace(reviewer_agent=FakeReviewer())
    monkeypatch.setitem(sys.modules, "agents.reviewer_agent", fake_module)

    state = pipeline.node_case_review({
        "feature": "Login",
        "source_bundle": {"prd_content": "Users can log in."},
        "test_cases": [{"scenario_id": "TC-001", "name": "Valid login"}],
    })

    assert state["case_review"]["status"] == "passed"
    assert state["case_review"]["quality_score"] == 8.5
    assert pipeline.route_after_case_review(state) == "approval_gate"
    assert calls == [
        (
            "Users can log in.",
            [{"scenario_id": "TC-001", "name": "Valid login"}],
            "Login",
            ["web"],
        )
    ]


def test_case_review_quality_gate_blocks_low_score(monkeypatch):
    class FakeReviewer:
        def review(self, prd_content, test_cases_json, feature, target_platforms=None):
            return SimpleNamespace(
                overall_quality_score=5.5,
                coverage_percentage=60.0,
                findings_critical=1,
                findings_major=2,
                findings_minor=0,
                detailed_findings=[{"severity": "Critical", "issue": "Missing invalid password test"}],
                missing_test_cases=["Missing invalid password test"],
                prd_clarifications=[],
                recommendation="revise",
                traceability_matrix=[],
            )

    fake_module = SimpleNamespace(reviewer_agent=FakeReviewer())
    monkeypatch.setitem(sys.modules, "agents.reviewer_agent", fake_module)

    state = pipeline.node_case_review({
        "feature": "Login",
        "source_bundle": {"prd_content": "Users can log in."},
        "test_cases": [{"scenario_id": "TC-001", "name": "Valid login"}],
    })

    assert state["case_review"]["status"] == "needs_revision"
    assert state["error"]["phase"] == "case_review"
    assert pipeline.route_after_case_review(state) == "report"


def test_case_review_does_not_block_android_plan_for_api_only_critical(monkeypatch):
    class FakeReviewer:
        def review(self, prd_content, test_cases_json, feature, target_platforms=None):
            assert target_platforms == ["android"]
            return SimpleNamespace(
                overall_quality_score=8.0,
                coverage_percentage=88.0,
                findings_critical=1,
                findings_major=0,
                findings_minor=0,
                missing_test_cases=[{
                    "priority": "P0",
                    "title": "Verify API payload excludes muted user IDs",
                    "reason": "Backend API contract should filter muted users.",
                }],
                prd_clarifications=[],
                recommendation="revise",
                traceability_matrix=[],
                detailed_findings=[{
                    "severity": "Critical",
                    "issue": "API response body schema coverage is missing.",
                }],
            )

    fake_module = SimpleNamespace(reviewer_agent=FakeReviewer())
    monkeypatch.setitem(sys.modules, "agents.reviewer_agent", fake_module)

    state = pipeline.node_case_review({
        "feature": "Profile Posts Tab Android",
        "platforms": ["android"],
        "source_bundle": {"prd_content": "Android Posts tab behavior."},
        "test_cases": [{"scenario_id": "TC-001", "name": "Open Posts tab"}],
    })

    assert state["case_review"]["status"] == "passed"
    assert state["case_review"]["scope_summary"]["blocking_critical_count"] == 0
    assert state["case_review"]["scope_summary"]["blocking_missing_count"] == 0
    assert state["case_review"]["scope_summary"]["cross_platform_risk_count"] == 2
    assert state["case_review"]["missing_test_cases"][0]["blocking"] is False
    assert pipeline.route_after_case_review(state) == "approval_gate"


def test_case_review_normalizes_0_to_100_score_and_exports_draft(monkeypatch, tmp_path):
    class FakeReviewer:
        def review(self, prd_content, test_cases_json, feature, target_platforms=None):
            return SimpleNamespace(
                overall_quality_score=71,
                coverage_percentage=68.0,
                findings_critical=1,
                findings_major=2,
                findings_minor=3,
                detailed_findings=[{"severity": "Critical", "issue": "Missing search block"}],
                missing_test_cases=[{"priority": "P0", "title": "Missing search block"}],
                prd_clarifications=[],
                recommendation="revise",
                traceability_matrix=[],
            )

    fake_module = SimpleNamespace(reviewer_agent=FakeReviewer())
    monkeypatch.setitem(sys.modules, "agents.reviewer_agent", fake_module)
    monkeypatch.chdir(tmp_path)

    state = pipeline.node_case_review({
        "feature": "Post Management",
        "run_id": "20260513_143153",
        "source_bundle": {"prd_content": "Users manage posts."},
        "test_cases": [{
            "scenario_id": "TC-001",
            "name": "Create post",
            "steps": [],
            "expected_result": "Post is visible",
        }],
    })

    assert state["case_review"]["status"] == "needs_revision"
    assert state["case_review"]["quality_score"] == 7.1
    assert state["case_review"]["quality_score_raw"] == 71
    assert state["draft_exports"]["json"].endswith("_needs_revision.json")
    assert state["draft_exports"]["csv"].endswith("_needs_revision.csv")
    assert Path(state["draft_exports"]["json"]).exists()
    assert Path(state["draft_exports"]["csv"]).exists()


def test_codegen_uses_existing_testcase_output(monkeypatch):
    output = _testcase_output()
    calls = []

    class FakeCodeGenerator:
        def run(self, testcase_output, platform, automation_evidence=None):
            calls.append((testcase_output, platform, automation_evidence))
            return {"features/login/test_login.py": "/tmp/test_login.py"}

    fake_module = SimpleNamespace(
        code_generator_agent=FakeCodeGenerator(),
    )
    monkeypatch.setitem(sys.modules, "agents.code_generator_agent", fake_module)

    state = pipeline.node_codegen({
        "feature": "Login",
        "platforms": ["web"],
        "testcase_output": output,
        "test_cases": [output.scenarios[0].model_dump(mode="json")],
    })

    assert state["generated_files"] == {
        "features/login/test_login.py": "/tmp/test_login.py"
    }
    assert calls == [(output, Platform.WEB, {})]


def test_testcase_export_uses_approved_testcase_output(monkeypatch, tmp_path):
    output = _testcase_output()
    calls = []
    csv_path = tmp_path / "test_plan_login.csv"
    excel_path = tmp_path / "test_plan_login.xlsx"

    class FakeExcelWriter:
        def write_both(self, testcase_output):
            calls.append(testcase_output)
            return {"csv": csv_path, "excel": excel_path}

    fake_module = SimpleNamespace(excel_writer=FakeExcelWriter())
    monkeypatch.setitem(sys.modules, "skills.reporting.excel_writer", fake_module)

    state = pipeline.node_testcase_export({
        "feature": "Login",
        "testcase_output": output,
        "approved": True,
    })

    assert state["testcase_exports"] == {
        "csv": str(csv_path),
        "excel": str(excel_path),
    }
    assert calls == [output]
    assert pipeline.route_after_testcase_export(state) == "automation_readiness_gate"


def test_automation_readiness_blocks_codegen_without_execution_evidence():
    state = pipeline.node_automation_readiness({
        "feature": "Profile Posts Tab Android",
        "platforms": ["android"],
        "testcase_exports": {"csv": "reports/test.csv"},
    })

    assert state["automation_readiness"]["status"] == "blocked"
    assert state["automation_readiness"]["codegen_allowed"] is False
    assert state["generated_files"] == {}
    assert state["error"]["phase"] == "automation_readiness"
    assert pipeline.route_after_automation_readiness(state) == "report"


def test_automation_readiness_allows_codegen_with_execution_evidence():
    state = pipeline.node_automation_readiness({
        "feature": "Profile Posts Tab Android",
        "platforms": ["android"],
        "testcase_exports": {"csv": "reports/test.csv"},
        "automation_evidence": {
            "android": {
                "flow_steps": ["Open profile", "Tap Posts tab"],
                "accessibility_ids": ["Profile", "Posts"],
                "test_data": {"user": "synthetic approved user"},
            }
        },
    })

    assert state["automation_readiness"]["status"] == "ready"
    assert state["automation_readiness"]["codegen_allowed"] is True
    assert state["error"] is None
    assert pipeline.route_after_automation_readiness(state) == "codegen"


def test_execute_reads_generated_file_dict_values(monkeypatch, tmp_path):
    test_file = tmp_path / "test_login.py"
    test_file.write_text("def test_login():\n    assert True\n")
    calls = []

    def fake_run(cmd, capture_output, text, check):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="passed", stderr="")

    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)

    state = pipeline.node_execute({
        "platforms": ["web"],
        "generated_files": {"relative.py": str(test_file)},
    })

    assert state["failures"] == []
    assert str(test_file) in state["execution_results"]
    assert calls[0][0] == pipeline.PYTHON_BIN
    assert calls[0][3] == str(test_file)


def test_testcase_node_stops_with_clear_error_when_agent_generates_zero(monkeypatch):
    class FakeTestCaseAgent:
        async def run(self, input_data, require_approval):
            return SimpleNamespace(
                scenarios=[],
                coverage_summary="JSON truncated — retry",
            )

    fake_module = SimpleNamespace(test_case_agent=FakeTestCaseAgent())
    monkeypatch.setitem(sys.modules, "agents.test_case_agent", fake_module)

    state = asyncio.run(pipeline.node_testcase({
        "feature": "Post Management",
        "platforms": ["android"],
        "acceptance_criteria": ["User can create a post."],
    }))

    assert state["current_phase"] == "testcase"
    assert state["test_cases"] == []
    assert state["error"]["phase"] == "testcase"
    assert "generated 0 scenarios" in state["error"]["message"]


def test_report_handles_none_optional_artifacts(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_QA_OPS_CHAT_ID", raising=False)

    state = pipeline.node_report({
        "feature": "HM 516",
        "run_id": "test-run",
        "test_cases": None,
        "testcase_exports": None,
        "generated_files": None,
        "failures": None,
        "coverage_gaps": None,
        "bug_reports": None,
        "case_review": {"status": "failed"},
        "coverage_percentage": None,
        "error": {"phase": "case_review", "message": "No test cases available"},
    })

    assert state["current_phase"] == "report"
    assert state["notifications"][-1] == {
        "channel": "qa_ops",
        "status": "FAILED",
        "sent": False,
    }


def test_report_handles_string_error_payload(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_QA_OPS_CHAT_ID", raising=False)

    state = pipeline.node_report({
        "feature": "Post Management",
        "coverage_percentage": None,
        "error": "Manual stop before codegen",
    })

    assert state["current_phase"] == "report"
    assert state["notifications"][-1]["status"] == "FAILED"


def test_report_uses_case_review_coverage_when_skill_gap_did_not_run(monkeypatch):
    messages = []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_QA_OPS_CHAT_ID", "chat")

    def fake_post(url, json, timeout):
        messages.append(json["text"])

    monkeypatch.setattr(pipeline.httpx, "post", fake_post)

    state = pipeline.node_report({
        "feature": "Post Management",
        "coverage_percentage": None,
        "case_review": {
            "status": "needs_revision",
            "coverage_percentage": 72.5,
            "findings": {"critical": 1, "major": 2, "minor": 3},
        },
        "error": {"phase": "case_review", "message": "Needs revision"},
    })

    assert state["notifications"][-1]["status"] == "FAILED"
    assert "*Coverage:* 72%" in messages[0]
