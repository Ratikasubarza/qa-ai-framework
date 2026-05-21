import hashlib
import hmac

from integrations.jira_webhook import webhook_server


def test_jira_webhook_signature_fails_closed_when_secret_missing(monkeypatch):
    monkeypatch.setattr(webhook_server, "JIRA_WEBHOOK_SECRET", "")
    monkeypatch.delenv("ALLOW_UNSIGNED_WEBHOOKS", raising=False)
    monkeypatch.setenv("TEST_ENV", "staging")

    assert webhook_server._verify_jira_signature(b"{}", "") is False


def test_jira_webhook_signature_allows_explicit_local_unsigned_mode(monkeypatch):
    monkeypatch.setattr(webhook_server, "JIRA_WEBHOOK_SECRET", "")
    monkeypatch.setenv("ALLOW_UNSIGNED_WEBHOOKS", "true")
    monkeypatch.setenv("TEST_ENV", "development")

    assert webhook_server._verify_jira_signature(b"{}", "") is True


def test_jira_webhook_signature_validates_hmac(monkeypatch):
    body = b'{"webhookEvent":"jira:issue_updated"}'
    secret = "test-secret"
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    monkeypatch.setattr(webhook_server, "JIRA_WEBHOOK_SECRET", secret)

    assert webhook_server._verify_jira_signature(body, f"sha256={signature}") is True
    assert webhook_server._verify_jira_signature(body, "sha256=wrong") is False
