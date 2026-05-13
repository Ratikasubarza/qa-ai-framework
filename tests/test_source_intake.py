from core.source_intake.intake import format_jira_issue_context
from core.source_intake.security import redact_internal_text
from core.source_intake.subtask_filter import filter_subtasks_for_platforms


def test_redact_internal_text_removes_secrets_and_personal_data():
    source = (
        "Authorization: Bearer abc.def.ghi\n"
        "Cookie: sessionid=secret-cookie\n"
        "api_key=super-secret\n"
        "email qa.user@example.com\n"
        "phone +62 812-3456-7890"
    )

    result = redact_internal_text(source)

    assert "abc.def.ghi" not in result.text
    assert "secret-cookie" not in result.text
    assert "super-secret" not in result.text
    assert "qa.user@example.com" not in result.text
    assert "+62 812-3456-7890" not in result.text
    assert "[REDACTED_AUTH_HEADER]" in result.text
    assert "[REDACTED_COOKIE]" in result.text
    assert "[REDACTED_EMAIL]" in result.text
    assert set(result.redactions) >= {
        "authorization_header",
        "cookie",
        "api_key",
        "email",
        "phone",
    }


def test_redact_internal_text_does_not_remove_plain_ids():
    result = redact_internal_text("Confluence page 37847042 and Jira HM-516")

    assert result.text == "Confluence page 37847042 and Jira HM-516"
    assert result.redactions == []


def test_filter_subtasks_for_platforms_keeps_matching_platform_only():
    subtasks = [
        {"key": "HM-1", "summary": "[BE] User Posts List API", "description": ""},
        {"key": "HM-2", "summary": "[Mobile] Profile Posts Tab - UI", "description": ""},
        {"key": "HM-3", "summary": "[FE] Profile Posts Tab - UI", "description": ""},
    ]

    filtered = filter_subtasks_for_platforms(subtasks, ["android"])

    assert [subtask["key"] for subtask in filtered] == ["HM-2"]


def test_filter_subtasks_for_platforms_falls_back_when_no_match():
    subtasks = [
        {"key": "HM-1", "summary": "Profile behavior task", "description": ""},
        {"key": "HM-2", "summary": "Content tab task", "description": ""},
    ]

    assert filter_subtasks_for_platforms(subtasks, ["android"]) == subtasks


def test_format_jira_issue_context_includes_filtered_subtasks():
    issue = {
        "key": "HM-516",
        "summary": "Profile content tabs",
        "status": "To Do",
        "priority": "Medium",
        "issue_type": "Story",
        "description": "Users can view profile tabs.",
        "acceptance_criteria": ["Posts tab displays user posts."],
        "subtasks": [
            {"key": "HM-1", "summary": "[BE] User Posts List API", "status": "Done"},
            {"key": "HM-2", "summary": "[Mobile] Profile Posts Tab - UI", "status": "Done"},
        ],
    }

    formatted = format_jira_issue_context(
        issue,
        include_subtasks=True,
        platforms=["android"],
    )

    assert "Developer Subtasks / Implementation Details for android" in formatted
    assert "HM-2: [Mobile] Profile Posts Tab - UI" in formatted
    assert "HM-1: [BE] User Posts List API" not in formatted
