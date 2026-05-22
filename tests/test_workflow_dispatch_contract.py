import asyncio
import sys
import types

from core.workflows.pending_approvals import PendingApprovalStore
from integrations.jira_webhook import webhook_server


def test_trigger_github_pipeline_uses_standardized_dispatch_inputs(monkeypatch):
    captured: dict = {}

    class FakeResponse:
        status_code = 204

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(webhook_server.httpx, "AsyncClient", lambda: FakeAsyncClient())

    status = asyncio.run(
        webhook_server.trigger_github_pipeline(
            test_suite="api",
            issue_key="HM-101",
            test_level="smoke",
            environment="staging",
        )
    )

    assert status == 204
    assert captured["url"].endswith("/actions/workflows/qa-pipeline.yml/dispatches")
    assert captured["json"]["inputs"] == {
        "environment": "staging",
        "test_suite": "api",
        "test_level": "smoke",
    }


def test_pending_approval_resolve_dispatches_canonical_resume_workflow(tmp_path, monkeypatch):
    calls: dict = {}

    class FakeGitHubClient:
        def trigger_workflow(self, workflow_id: str, inputs: dict, ref: str = "main") -> bool:
            calls["workflow_id"] = workflow_id
            calls["inputs"] = inputs
            calls["ref"] = ref
            return True

    monkeypatch.setitem(
        sys.modules,
        "integrations.github_client",
        types.SimpleNamespace(github_client=FakeGitHubClient()),
    )

    store = PendingApprovalStore(store_dir=tmp_path)
    store.save(
        approval_id="HM-777_1",
        state={
            "feature": "Login",
            "environment": "dev",
            "test_suite": "api",
        },
    )
    resolved = store.resolve("HM-777_1", decision="approve", reason="Looks good")

    assert resolved is True
    assert calls["workflow_id"] == "qa-pipeline.yml"
    assert calls["ref"] == "main"
    assert calls["inputs"] == {
        "environment": "dev",
        "test_suite": "api",
        "test_level": "approval_resume",
    }
