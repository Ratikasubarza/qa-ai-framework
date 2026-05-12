import json

from agents.test_case_agent import TestCaseAgent
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
    assert scenario.edge_cases == ["title exactly at maximum length"]
    assert scenario.combination_edge_cases == ["maximum title with optional image omitted"]
    assert scenario.weird_edge_cases == ["rapidly tap submit twice"]
