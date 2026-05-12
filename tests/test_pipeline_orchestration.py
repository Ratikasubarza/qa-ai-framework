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
