import asyncio
import json
from types import SimpleNamespace

from agents import test_case_agent as test_case_agent_module
from agents.test_case_agent import MAX_AC_PER_BATCH, TestCaseAgent
from core.agent_contracts import Platform, TestCaseAgentInput


def test_parse_output_preserves_three_edge_case_categories():
    agent = TestCaseAgent()
    input_data = TestCaseAgentInput(
        feature="Post Management",
        description="Users can create posts.",
        platforms=[Platform.ANDROID],
        acceptance_criteria=["User can create a post with optional image."],
    )
    raw = json.dumps({
        "feature": "Post Management",
        "scenarios": [
            {
                "case_id": "TC-001",
                "title": "Create post at title length boundary",
                "preconditions": "User is logged in on Android.",
                "steps": [
                    {
                        "step_number": 1,
                        "action": "Create a post with a 255-character title",
                        "expected": "Post is accepted",
                    }
                ],
                "expected_result": "Post appears in profile.",
                "priority": "P1",
                "tags": ["edge cases", "combination edge", "weird edge"],
                "platform": "MOBILE",
                "test_type": "boundary",
                "edge_cases": ["title exactly at maximum length"],
                "combination_edge_cases": ["maximum title with optional image omitted"],
                "weird_edge_cases": ["rapidly tap submit twice"],
            }
        ],
        "coverage_summary": "All edge categories covered.",
    })

    output = agent._parse_output(raw, input_data, "fake-model")
    scenario = output.scenarios[0]

    assert scenario.platforms == [Platform.ANDROID]
    assert scenario.test_type.value == "boundary"
    assert scenario.edge_cases == ["title exactly at maximum length"]
    assert scenario.combination_edge_cases == ["maximum title with optional image omitted"]
    assert scenario.weird_edge_cases == ["rapidly tap submit twice"]
    assert scenario.regression_candidate is False


def test_parse_output_defaults_new_feature_cases_to_functional():
    agent = TestCaseAgent()
    input_data = TestCaseAgentInput(
        feature="Post Management",
        description="Users can create posts.",
        platforms=[Platform.ANDROID],
        acceptance_criteria=["User can create a post."],
    )
    raw = json.dumps({
        "feature": "Post Management",
        "scenarios": [
            {
                "case_id": "TC-001",
                "title": "Create post with title and body",
                "preconditions": "User is logged in.",
                "steps": "Given user is on Create Post\nWhen user submits a valid post\nThen post is created",
                "expected_result": "Post appears in profile.",
                "priority": "P1",
                "platform": "MOBILE",
            }
        ],
    })

    output = agent._parse_output(raw, input_data, "fake-model")
    scenario = output.scenarios[0]

    assert scenario.test_type.value == "functional"
    assert scenario.regression_candidate is False
    assert scenario.regression_risk_area == []


def test_parse_output_marks_regression_candidates_with_risk_area():
    agent = TestCaseAgent()
    input_data = TestCaseAgentInput(
        feature="Post Management",
        description="Creating posts should not break profile.",
        platforms=[Platform.ANDROID],
        acceptance_criteria=["Existing profile content still appears."],
    )
    raw = json.dumps({
        "feature": "Post Management",
        "scenarios": [
            {
                "case_id": "TC-REG-001",
                "title": "Existing profile media remains visible after post creation",
                "preconditions": "User has existing uploaded media.",
                "steps": "Given user created a post\nWhen user opens profile\nThen existing media remains visible",
                "expected_result": "Existing media is unchanged.",
                "priority": "P1",
                "platform": "MOBILE",
                "test_type": "regression",
                "regression_candidate": True,
                "regression_risk_area": ["profile media grid"],
            }
        ],
    })

    output = agent._parse_output(raw, input_data, "fake-model")
    scenario = output.scenarios[0]

    assert scenario.test_type.value == "regression"
    assert scenario.regression_candidate is True
    assert scenario.regression_risk_area == ["profile media grid"]


def test_parse_output_recovers_complete_scenarios_from_truncated_json():
    agent = TestCaseAgent()
    input_data = TestCaseAgentInput(
        feature="Post Management",
        description="Posts tab pagination.",
        platforms=[Platform.ANDROID],
        acceptance_criteria=["Posts tab loads paginated results."],
    )
    raw = """
    {
      "feature": "Post Management",
      "scenarios": [
        {
          "case_id": "TC-001",
          "title": "Load first page",
          "preconditions": "User is logged in.",
          "steps": "Given user opens Posts tab\\nWhen first page loads\\nThen posts are visible",
          "expected_result": "First page is displayed.",
          "priority": "P1",
          "platform": "android"
        },
        {
          "case_id": "TC-002",
          "title": "Load next page",
          "preconditions": "User is logged in.",
          "steps": "Given user is on Posts tab\\nWhen user scrolls near bottom\\nThen more posts load",
          "expected_result": "Next page is appended.",
          "priority": "P1",
          "platform": "android"
        },
        {
          "case_id": "TC-003",
          "title": "Incomplete final case",
          "preconditions": "User is logged in.",
          "steps": "Given
    """

    output = agent._parse_output(raw, input_data, "fake-model")

    assert output.total_scenarios == 2
    assert [scenario.scenario_id for scenario in output.scenarios] == ["TC-001", "TC-002"]
    assert output.coverage_summary == "Recovered complete scenarios from truncated JSON."


def test_chunked_generation_merges_and_renumbers_scenarios(monkeypatch):
    agent = TestCaseAgent()
    input_data = TestCaseAgentInput(
        feature="Post Management",
        description="Large PRD",
        platforms=[Platform.ANDROID],
        acceptance_criteria=[
            f"AC {index}: User can validate post behavior {index}"
            for index in range(MAX_AC_PER_BATCH + 1)
        ],
    )
    calls = []

    monkeypatch.setattr(
        test_case_agent_module.rag_engine,
        "retrieve",
        lambda query, top_k: "",
    )
    monkeypatch.setattr(
        test_case_agent_module.prompt_manager,
        "get",
        lambda name: (
            "FEATURE: {feature}\nDESCRIPTION: {description}\nPLATFORMS: {platforms}\n"
            "ACCEPTANCE CRITERIA:\n{acceptance_criteria}\nPAST CONTEXT:\n{past_context}\nDATE: {date}"
        ),
    )

    def fake_complete_text(system, user, tier, agent_name, json_mode):
        calls.append((system, user))
        return SimpleNamespace(
            content=json.dumps({
                "feature": "Post Management",
                "scenarios": [
                    {
                        "case_id": "TC-LOCAL",
                        "title": f"Scenario from batch {len(calls)}",
                        "preconditions": "User is logged in.",
                        "steps": "Given user is logged in\nWhen user opens posts\nThen posts are visible",
                        "expected_result": "Posts are visible.",
                        "platform": "MOBILE",
                        "test_type": "functional",
                    }
                ],
                "coverage_summary": f"batch {len(calls)} covered",
            }),
            model="fake-model",
            tokens_used=10,
        )

    monkeypatch.setattr(test_case_agent_module.llm_client, "complete_text", fake_complete_text)

    output = asyncio.run(agent.run(input_data, require_approval=False))

    assert len(calls) == 2
    assert [scenario.scenario_id for scenario in output.scenarios] == ["TC-001", "TC-002"]
    assert output.total_scenarios == 2
    assert output.tokens_used == 20
    assert "batch 1 covered" in output.coverage_summary
    assert "batch 2 covered" in output.coverage_summary
