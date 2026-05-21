"""
Pydantic schema for inbound Jira webhook payloads.

Validates the shape of every incoming event before it reaches any business
logic. Unknown fields are allowed (extra="allow") because Jira adds fields
freely across versions; we only enforce the fields we actually use.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class JiraIssueType(BaseModel):
    name: str = ""
    model_config = {"extra": "allow"}


class JiraStatus(BaseModel):
    name: str = ""
    model_config = {"extra": "allow"}


class JiraPriority(BaseModel):
    name: str = ""
    model_config = {"extra": "allow"}


class JiraAssignee(BaseModel):
    displayName: str = ""
    emailAddress: str = ""
    model_config = {"extra": "allow"}


class JiraIssueFields(BaseModel):
    summary:     str                  = ""
    description: Optional[str]        = None
    status:      Optional[JiraStatus]   = None
    priority:    Optional[JiraPriority] = None
    assignee:    Optional[JiraAssignee] = None
    issuetype:   Optional[JiraIssueType] = None
    labels:      list[str]            = Field(default_factory=list)

    model_config = {"populate_by_name": True, "extra": "allow"}


class JiraIssue(BaseModel):
    id:     str
    key:    str
    fields: JiraIssueFields = Field(default_factory=JiraIssueFields)

    model_config = {"extra": "allow"}


class JiraSprint(BaseModel):
    id:   Optional[int]  = None
    name: Optional[str]  = None
    model_config = {"extra": "allow"}


class JiraWebhookEvent(BaseModel):
    """
    Top-level Jira webhook payload.

    Jira delivers events with `webhookEvent` as the discriminator.
    We validate that issue-level events carry an issue object; sprint
    events carry a sprint object.
    """
    webhookEvent:          str
    issue_event_type_name: Optional[str]       = None
    timestamp:             Optional[int]        = None   # epoch ms — used for replay protection
    issue:                 Optional[JiraIssue]  = None
    changelog:             Optional[dict]        = None
    sprint:                Optional[JiraSprint]  = None

    model_config = {"extra": "allow"}

    @model_validator(mode="after")
    def validate_payload_completeness(self) -> "JiraWebhookEvent":
        issue_events = {"jira:issue_updated", "jira:issue_created"}
        if self.webhookEvent in issue_events and self.issue is None:
            raise ValueError(
                f"Jira event '{self.webhookEvent}' must include an 'issue' object."
            )
        if self.webhookEvent == "sprint_started" and self.sprint is None:
            raise ValueError("sprint_started event must include a 'sprint' object.")
        return self

    # ── Convenience accessors ──────────────────────────────────────────────

    @property
    def issue_key(self) -> str:
        return self.issue.key if self.issue else ""

    @property
    def issue_summary(self) -> str:
        return self.issue.fields.summary if self.issue else ""

    @property
    def issue_type_name(self) -> str:
        if self.issue and self.issue.fields.issuetype:
            return self.issue.fields.issuetype.name.lower()
        return ""

    @property
    def new_status(self) -> str:
        """Extract the new status value from a changelog items list."""
        if not self.changelog:
            return ""
        for item in self.changelog.get("items", []):
            if item.get("field") == "status":
                return item.get("toString", "").upper()
        return ""
