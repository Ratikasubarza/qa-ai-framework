import sys
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
    assert bundle["intake_quality"] == {
        "has_ticket": True,
        "has_prd_content": True,
        "has_feature_url": True,
    }


def test_case_review_quality_gate_passes(monkeypatch):
    calls = []

    class FakeReviewer:
        def review(self, prd_content, test_cases_json, feature):
            calls.append((prd_content, test_cases_json, feature))
            return SimpleNamespace(
                overall_quality_score=8.5,
                coverage_percentage=90.0,
                findings_critical=0,
                findings_major=1,
                findings_minor=2,
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
    assert pipeline.route_after_case_review(state) == "approval"
    assert calls == [
        (
            "Users can log in.",
            [{"scenario_id": "TC-001", "name": "Valid login"}],
            "Login",
        )
    ]


def test_case_review_quality_gate_blocks_low_score(monkeypatch):
    class FakeReviewer:
        def review(self, prd_content, test_cases_json, feature):
            return SimpleNamespace(
                overall_quality_score=5.5,
                coverage_percentage=60.0,
                findings_critical=1,
                findings_major=2,
                findings_minor=0,
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


def test_codegen_uses_existing_testcase_output(monkeypatch):
    output = _testcase_output()
    calls = []

    class FakeCodeGenerator:
        def run(self, testcase_output, platform):
            calls.append((testcase_output, platform))
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
    assert calls == [(output, Platform.WEB)]


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
    assert pipeline.route_after_testcase_export(state) == "codegen"


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
