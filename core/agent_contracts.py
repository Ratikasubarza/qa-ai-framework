"""
Agent Contracts — typed Pydantic I/O schemas for every agent boundary.
Every agent input and output must validate against these schemas.
Schema mismatch fails loudly at the boundary, not silently downstream.
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


# ── Enums ──────────────────────────────────────────────────────────────────

class Platform(str, Enum):
    WEB              = "web"
    API              = "api"
    ANDROID          = "android"
    IOS              = "ios"
    FLUTTER_ANDROID  = "flutter-android"
    FLUTTER_IOS      = "flutter-ios"
    DATABASE         = "database"


class TestType(str, Enum):
    SMOKE      = "smoke"
    FUNCTIONAL = "functional"
    REGRESSION = "regression"
    E2E        = "e2e"
    NEGATIVE   = "negative"
    BOUNDARY   = "boundary"


class Priority(str, Enum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"


class Decision(str, Enum):
    APPROVE = "approve"
    EDIT    = "edit"
    REJECT  = "reject"


# ── Test Case Schemas ──────────────────────────────────────────────────────

class TestStep(BaseModel):
    step_number: int
    action:      str
    expected:    str


class ScenarioSchema(BaseModel):
    scenario_id:  str
    name:         str
    precondition: str
    steps:        list[TestStep]
    expected_result: str
    test_data:    dict             = Field(default_factory=dict)
    tags:         list[str]       = Field(default_factory=list)
    test_type:    TestType        = TestType.FUNCTIONAL
    platforms:    list[Platform]  = Field(default_factory=list)
    priority:     Priority        = Priority.MEDIUM
    edge_cases:   list[str]       = Field(default_factory=list)
    combination_edge_cases: list[str] = Field(default_factory=list)
    weird_edge_cases: list[str] = Field(default_factory=list)
    regression_candidate: bool = False
    regression_risk_area: list[str] = Field(default_factory=list)


class TestCaseAgentInput(BaseModel):
    feature:         str
    description:     str
    acceptance_criteria: list[str] = Field(default_factory=list)
    platforms:       list[Platform]
    jira_story_key:  Optional[str] = None
    context:         Optional[str] = None  # Extra context for the agent


class TestCaseAgentOutput(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    feature:          str
    scenarios:        list[ScenarioSchema]
    coverage_summary: str
    total_scenarios:  int
    # Provenance — required for audit trail
    prompt_version:   str
    model_used:       str
    generated_at:     datetime = Field(default_factory=datetime.now)
    tokens_used:      int      = 0


# ── AC Extraction Schemas ──────────────────────────────────────────────────

class AmbiguityFlag(BaseModel):
    field:              str  # Which part of the story is unclear
    description:        str  # Why it is ambiguous
    impact:             str  # What test coverage is blocked
    suggested_question: str  # Exact question to ask the PO


class AssumptionNote(BaseModel):
    assumption: str  # What was assumed
    based_on:   str  # Which past feature/bug informed this
    risk:       str  # What breaks if assumption is wrong


class AcceptanceCriteria(BaseModel):
    ac_id:        str
    summary:      str
    given:        str
    when:         list[str]
    then:         list[str]
    edge_cases:   list[str]      = Field(default_factory=list)
    test_types:   list[TestType] = Field(default_factory=list)
    platforms:    list[Platform] = Field(default_factory=list)
    priority:     Priority       = Priority.MEDIUM
    dependencies: list[str]      = Field(default_factory=list)


class AcceptanceCriteriaOutput(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    source_ref:   str
    feature:      str
    criteria:     list[AcceptanceCriteria]
    ambiguities:  list[AmbiguityFlag]   = Field(default_factory=list)
    assumptions:  list[AssumptionNote]  = Field(default_factory=list)
    out_of_scope: list[str]             = Field(default_factory=list)
    missing_data: list[str]             = Field(default_factory=list)
    prompt_version: str  = ""
    model_used:     str  = ""
    generated_at:   datetime = Field(default_factory=datetime.now)


# ── Jira Ticket Schemas ────────────────────────────────────────────────────

class QATicketDraft(BaseModel):
    title:        str
    issue_type:   str        = "Task"
    priority:     str        = "Medium"
    labels:       list[str]  = Field(default_factory=list)
    components:   list[str]  = Field(default_factory=list)
    parent_key:   Optional[str] = None
    linked_story: Optional[str] = None
    test_type:    TestType   = TestType.FUNCTIONAL
    platform:     Platform   = Platform.WEB
    precondition: str        = ""
    steps:        list[str]  = Field(default_factory=list)
    expected:     str        = ""
    test_data:    str        = ""
    edge_cases:   list[str]  = Field(default_factory=list)
    source_ac_id: str        = ""
    generated_by: str        = "RequirementsAgent"
    prompt_version: str      = ""
    automation_candidate: bool = False
    automation_reason:    str  = ""


# ── Locator / Self-Heal Schemas ────────────────────────────────────────────

class LocatorHealOutput(BaseModel):
    feature:     str
    broken_locator: str
    candidates:  list[str]     # 3 candidates ordered by confidence
    applied:     Optional[str] = None
    snapshot_id: str           # For rollback
    healed:      bool          = False
    attempts:    int           = 0


# ── Feedback Schema ────────────────────────────────────────────────────────

class RejectionReason(str, Enum):
    MISSING_EDGE_CASE   = "missing_edge_case"
    WRONG_ASSERTION     = "wrong_assertion"
    WRONG_PLATFORM      = "wrong_platform"
    HALLUCINATED_STEP   = "hallucinated_step"
    INCOMPLETE_SCENARIO = "incomplete_scenario"
    WRONG_TEST_DATA     = "wrong_test_data"


class AgentFeedback(BaseModel):
    output_id:            str
    decision:             Decision
    rejection_reason:     Optional[RejectionReason] = None
    missing_coverage:     list[str]  = Field(default_factory=list)
    wrong_assertion_type: bool       = False
    corrected_output:     Optional[str] = None
    reviewer_id:          str        = "unknown"
    reviewed_at:          datetime   = Field(default_factory=datetime.now)
