import asyncio
import sys
import types

from core.agent_contracts import Platform, TestCaseAgentInput
from core.schemas.jira_webhook_schema import JiraWebhookEvent
from integrations.jira_webhook import webhook_server


def test_handle_new_bug_uses_testcase_agent_input_contract(monkeypatch):
    captured = {"comment": "", "telegram": ""}

    class FakeTestCaseAgent:
        def __init__(self):
            self.received = None
            self.require_approval = None

        async def run(self, payload, require_approval=False):
            self.received = payload
            self.require_approval = require_approval
            return types.SimpleNamespace(
                scenarios=[
                    types.SimpleNamespace(name="API bug scenario"),
                    types.SimpleNamespace(name="Regression scenario"),
                ]
            )

    fake_agent = FakeTestCaseAgent()
    monkeypatch.setitem(
        sys.modules,
        "agents.test_case_agent",
        types.SimpleNamespace(test_case_agent=fake_agent),
    )

    async def _fake_comment(issue_key: str, comment: str):
        captured["comment"] = comment

    async def _fake_telegram(message: str):
        captured["telegram"] = message

    monkeypatch.setattr(webhook_server, "add_jira_comment", _fake_comment)
    monkeypatch.setattr(webhook_server, "send_telegram", _fake_telegram)

    event = JiraWebhookEvent.model_validate(
        {
            "webhookEvent": "jira:issue_created",
            "issue": {
                "id": "1001",
                "key": "HM-999",
                "fields": {
                    "summary": "API returns 500 for valid token",
                    "description": "Observed in staging environment",
                    "issuetype": {"name": "Bug"},
                    "labels": ["api", "critical"],
                },
            },
        }
    )

    asyncio.run(webhook_server.handle_new_bug(event))

    assert isinstance(fake_agent.received, TestCaseAgentInput)
    assert fake_agent.received.jira_story_key == "HM-999"
    assert fake_agent.received.platforms == [Platform.API]
    assert fake_agent.require_approval is False
    assert "API bug scenario" in captured["comment"]
    assert "New Bug" in captured["telegram"]


def test_infer_bug_platforms_defaults_to_web_when_label_missing():
    event = JiraWebhookEvent.model_validate(
        {
            "webhookEvent": "jira:issue_created",
            "issue": {
                "id": "1002",
                "key": "HM-1000",
                "fields": {
                    "summary": "Unexpected crash in profile flow",
                    "description": "Crash report attached",
                    "issuetype": {"name": "Bug"},
                    "labels": [],
                },
            },
        }
    )

    platforms = webhook_server._infer_bug_platforms(event)

    assert platforms == ["web"]
