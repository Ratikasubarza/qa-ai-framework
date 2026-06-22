"""
Test Plan Agent — intelligently selects testing techniques based on requirements analysis.

Auto-selects from: decision_table, pairwise, equivalence_partitioning,
boundary_value_analysis, state_transition, error_guessing.

Techniques are NOT all-applied by default — each is selected only when the
requirements text exhibits patterns that warrant it.
"""
from __future__ import annotations

import json
import re
import structlog
from datetime import datetime
from pathlib import Path

from core.llm_client import llm_client, ModelTier
from core.agent_contracts import (
    TestPlanOutput, TestScenario, DecisionTableRow, PairwiseRow,
)
from core.circuit_breaker import get_breaker
from core.input_sanitizer import sanitize

logger = structlog.get_logger(__name__)

AGENT_NAME     = "test_plan_agent"
PROMPT_VERSION = "1.0.0"

# ── Technique selection patterns ──────────────────────────────────────────────

# Decision Table: multiple interacting boolean conditions
_DT_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r"if\s+\w[\w\s]+and\s+.+then",
    r"based\s+on\s+.+\s+and",
    r"\bcombination\b",
    r"\bpermission\b",
    r"\brole\b",
    r"\bpremium\b",
    r"depending\s+on",
]]

# Pairwise: independent configurable parameters (3+ triggers selection)
_PAIRWISE_PARAMS = [
    "platform", "browser", "device", "user_type", "language",
    "region", "plan_type", "filter", "configuration",
]

# Boundary Value Analysis: numeric / length constraints
_BVA_KEYWORDS = [
    "limit", "maximum", "minimum", "characters", "length", "range",
    "between", "age", "amount", "price", "quota", "threshold",
    "at least", "up to",
]

# State Transition: stateful workflows
_ST_KEYWORDS = [
    "status", "state", "workflow", "approve", "reject", "verify",
    "activate", "deactivate", "pending", "transition", "lifecycle",
    "progress",
]


class TestPlanAgent:
    """
    Generates a structured test plan by intelligently selecting testing techniques
    based on the requirements text. Techniques are not hardcoded — each is selected
    only when the requirements exhibit patterns that warrant it.

    Usage:
        agent = TestPlanAgent()
        output = agent.create_test_plan({
            "feature_name": "User Login",
            "ticket_id": "HM-42",
            "acceptance_criteria": ["User can log in with email/password"],
            "description": "...",
            "platforms": ["api", "web"],
        })
    """

    def __init__(self) -> None:
        self.breaker = get_breaker(AGENT_NAME)

    def create_test_plan(self, requirements: dict) -> TestPlanOutput:
        """
        Main entry point. Analyses requirements, selects techniques,
        generates scenarios via LLM, returns typed TestPlanOutput.

        Args:
            requirements: dict with keys:
                feature_name (str), ticket_id (str, optional),
                acceptance_criteria (list[str]), description (str),
                platforms (list[str], optional).

        Returns:
            TestPlanOutput with full test plan, rationale, and metadata.
        """
        feature_name = requirements.get("feature_name", "")
        ticket_id    = requirements.get("ticket_id", "")

        logger.info(
            "test_plan_agent_start",
            feature=feature_name,
            ticket=ticket_id,
            ac_count=len(requirements.get("acceptance_criteria", [])),
        )

        techniques = self._select_techniques(requirements)
        logger.info("techniques_selected", feature=feature_name, techniques=techniques)

        output = self._generate_scenarios(requirements, techniques)

        logger.info(
            "test_plan_complete",
            feature=feature_name,
            techniques=output.techniques_used,
            scenarios=output.total_scenarios,
            coverage=output.estimated_coverage_percent,
        )
        return output

    def _select_techniques(self, requirements: dict) -> list[str]:
        """
        Analyse requirements text and return applicable technique names.

        Equivalence partitioning and error guessing are always included as baseline.
        All others are triggered by keyword / pattern detection.
        """
        ac_text   = "\n".join(requirements.get("acceptance_criteria", []))
        full_text = " ".join([
            requirements.get("description", ""),
            requirements.get("feature_name", ""),
            ac_text,
        ]).lower()

        # Always-on baseline techniques
        techniques: list[str] = ["equivalence_partitioning", "error_guessing"]

        # Decision Table: multiple interacting boolean conditions
        if any(p.search(full_text) for p in _DT_PATTERNS):
            techniques.append("decision_table")

        # Pairwise: 3+ independent configurable parameters
        if sum(1 for kw in _PAIRWISE_PARAMS if kw in full_text) >= 3:
            techniques.append("pairwise")

        # Boundary Value Analysis: numeric / length constraints
        if any(kw in full_text for kw in _BVA_KEYWORDS):
            techniques.append("boundary_value_analysis")

        # State Transition: stateful workflows
        if any(kw in full_text for kw in _ST_KEYWORDS):
            techniques.append("state_transition")

        return techniques

    def _build_prompt(self, requirements: dict, techniques: list[str]) -> str:
        """
        Construct the LLM system prompt. All external strings are sanitized
        before embedding — mandatory security requirement.
        """
        feature_name = sanitize(
            requirements.get("feature_name", ""), source="feature_name"
        ).content
        ticket_id = sanitize(
            requirements.get("ticket_id", ""), source="ticket_id"
        ).content
        description = sanitize(
            requirements.get("description", "")[:1500], source="description"
        ).content

        sanitized_ac = "\n".join(
            f"- {sanitize(ac, source='ac').content}"
            for ac in requirements.get("acceptance_criteria", [])
        ) or "Not provided"

        techniques_json = json.dumps(techniques)

        # Technique-specific instructions — only emitted when technique is selected
        dt_block = (
            "\nFor Decision Table:\n"
            "- List all conditions (each row = one condition, Y/N)\n"
            "- List all rules (each column = one combination)\n"
            "- Mark which action applies per rule\n"
            "- Generate one test case per unique rule column\n"
        ) if "decision_table" in techniques else ""

        pw_block = (
            "\nFor Pairwise Testing:\n"
            "- List all parameters and their possible values\n"
            "- Show the reduced pairwise matrix\n"
            "- Generate one test case per matrix row\n"
        ) if "pairwise" in techniques else ""

        bva_block = (
            "\nFor Boundary Value Analysis:\n"
            "- For each constrained field: min-1, min, min+1, typical, max-1, max, max+1\n"
            "- Generate one test case per boundary value\n"
        ) if "boundary_value_analysis" in techniques else ""

        st_block = (
            "\nFor State Transition:\n"
            "- List all states\n"
            "- List all valid transitions (state + event -> new state)\n"
            "- List all invalid transitions (should be rejected)\n"
            "- Generate one test case per transition\n"
        ) if "state_transition" in techniques else ""

        # JSON output template — braces doubled to avoid format() collisions
        json_template = (
            "{{\n"
            '  "techniques_used": {techniques_json},\n'
            '  "technique_rationale": {{\n'
            '    "equivalence_partitioning": "why always included",\n'
            '    "error_guessing": "why always included"\n'
            "  }},\n"
            '  "scenarios": [\n'
            "    {{\n"
            '      "scenario_id": "TC-001",\n'
            '      "scenario_name": "descriptive name of what is being tested",\n'
            '      "technique": "which technique generated this",\n'
            '      "type": "happy_path|negative|edge_case|boundary|state_transition",\n'
            '      "priority": "P1|P2|P3",\n'
            '      "platforms": ["api", "web", "android"],\n'
            '      "preconditions": ["user is registered and verified"],\n'
            '      "inputs": {{"field": "value"}},\n'
            '      "expected_outcome": "exact expected result",\n'
            '      "risk_level": "high|medium|low",\n'
            '      "tags": ["smoke", "regression"]\n'
            "    }}\n"
            "  ],\n"
            '  "decision_table": [],\n'
            '  "pairwise_matrix": [],\n'
            '  "state_diagram": {{}},\n'
            '  "coverage_per_ac": {{}},\n'
            '  "total_scenarios": 0,\n'
            '  "estimated_coverage_percent": 0,\n'
            '  "test_data_requirements": ["approved user account"],\n'
            '  "environment_prerequisites": ["staging DB accessible"],\n'
            '  "entry_criteria": ["feature deployed to staging"],\n'
            '  "exit_criteria": ["all P1 passed", "coverage >=90%"],\n'
            '  "estimated_execution_time_minutes": 0\n'
            "}}"
        ).format(techniques_json=techniques_json)

        return (
            "You are a Senior QA Engineer. Generate a structured test plan.\n\n"
            f"Feature: {feature_name}\n"
            f"Ticket: {ticket_id}\n"
            f"Acceptance Criteria:\n{sanitized_ac}\n"
            f"Description: {description}\n\n"
            f"Apply ONLY these selected techniques: {techniques_json}\n\n"
            "For each technique, explain WHY it was chosen for this feature.\n"
            + dt_block
            + pw_block
            + "\nFor Equivalence Partitioning (always):\n"
            "- List valid partitions and invalid partitions per input field\n"
            "- Generate one test case per partition\n"
            + bva_block
            + st_block
            + "\nFor Error Guessing (always):\n"
            "- Add scenarios for: empty, null, max+1, special chars (!@#$%),\n"
            "  unicode/emoji, concurrent same action, session expiry mid-flow,\n"
            "  network drop mid-operation, duplicate submission\n\n"
            "Output ONLY valid JSON. No markdown. No explanation outside JSON.\n"
            f"Format:\n{json_template}"
        )

    def _generate_scenarios(
        self, requirements: dict, techniques: list[str]
    ) -> TestPlanOutput:
        """
        Call LLM via circuit breaker, parse the response into TestPlanOutput.
        Falls back to an empty-but-valid output on LLM failure.
        """
        feature_name  = requirements.get("feature_name", "")
        ticket_id     = requirements.get("ticket_id", "")
        system_prompt = self._build_prompt(requirements, techniques)

        model_used  = "unknown"
        tokens_used = 0

        def _call():
            return llm_client.complete_text(
                system=system_prompt,
                user=f"Generate test plan for: {feature_name} (Ticket: {ticket_id})",
                tier=ModelTier.COMPLEX,
                agent_name=AGENT_NAME,
                json_mode=True,
            )

        try:
            response    = self.breaker.call(_call)
            model_used  = response.model
            tokens_used = response.tokens_used
            raw         = (response.content or "").strip()
            raw         = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
            data        = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("test_plan_json_parse_failed", feature=feature_name, error=str(e))
            data = self._fallback_output(techniques)
        except Exception as e:
            logger.error("test_plan_llm_failed", feature=feature_name, error=str(e))
            data = self._fallback_output(techniques)

        return self._parse_output(data, requirements, techniques, model_used, tokens_used)

    def _parse_output(
        self,
        data:        dict,
        requirements: dict,
        techniques:  list[str],
        model_used:  str,
        tokens_used: int,
    ) -> TestPlanOutput:
        """Parse LLM JSON response dict into a typed TestPlanOutput."""
        feature_name = requirements.get("feature_name", "")
        ticket_id    = requirements.get("ticket_id", "")

        # ── Parse scenarios ───────────────────────────────────────────
        _valid_types   = {"happy_path", "negative", "edge_case", "boundary", "state_transition"}
        _valid_prio    = {"P1", "P2", "P3"}
        _valid_risk    = {"high", "medium", "low"}

        scenarios: list[TestScenario] = []
        for i, s in enumerate(data.get("scenarios", []), 1):
            if not isinstance(s, dict):
                continue
            try:
                sc_type  = s.get("type", "edge_case")
                priority = s.get("priority", "P2")
                risk     = s.get("risk_level", "medium")

                scenarios.append(TestScenario(
                    scenario_id      = s.get("scenario_id", f"TC-{i:03d}"),
                    scenario_name    = s.get("scenario_name", f"Scenario {i}"),
                    technique        = s.get("technique", "equivalence_partitioning"),
                    type             = sc_type if sc_type in _valid_types else "edge_case",
                    priority         = priority if priority in _valid_prio else "P2",
                    platforms        = [str(p) for p in s.get("platforms", [])],
                    preconditions    = [str(p) for p in s.get("preconditions", [])],
                    inputs           = s.get("inputs", {}) if isinstance(s.get("inputs"), dict) else {},
                    expected_outcome = s.get("expected_outcome", ""),
                    risk_level       = risk if risk in _valid_risk else "medium",
                    tags             = [str(t) for t in s.get("tags", [])],
                ))
            except Exception as exc:
                logger.warning(
                    "test_plan_scenario_parse_error", index=i, error=str(exc)
                )

        # ── Parse decision table ──────────────────────────────────────
        dt_rows: list[DecisionTableRow] = []
        for row in data.get("decision_table", []):
            if isinstance(row, dict) and "condition" in row:
                dt_rows.append(DecisionTableRow(
                    condition=str(row.get("condition", "")),
                    rules=[str(r) for r in row.get("rules", [])],
                ))

        # ── Parse pairwise matrix ─────────────────────────────────────
        pw_rows: list[PairwiseRow] = []
        for i, row in enumerate(data.get("pairwise_matrix", []), 1):
            if not isinstance(row, dict):
                continue
            row_copy = dict(row)
            tc_id    = str(row_copy.pop("test_case_id", f"PW-{i:03d}"))
            pw_rows.append(PairwiseRow(
                parameters   = {k: str(v) for k, v in row_copy.items()},
                test_case_id = tc_id,
            ))

        # ── Parse coverage_per_ac — values may be int or float ────────
        raw_coverage = data.get("coverage_per_ac", {})
        coverage_per_ac: dict[str, float] = {}
        if isinstance(raw_coverage, dict):
            for k, v in raw_coverage.items():
                try:
                    coverage_per_ac[str(k)] = float(v)
                except (TypeError, ValueError):
                    pass

        total = len(scenarios)

        return TestPlanOutput(
            feature_name                  = feature_name,
            ticket_id                     = ticket_id,
            techniques_used               = data.get("techniques_used", techniques),
            technique_rationale           = data.get("technique_rationale", {}),
            scenarios                     = scenarios,
            decision_table                = dt_rows,
            pairwise_matrix               = pw_rows,
            state_diagram                 = data.get("state_diagram", {}),
            coverage_per_ac               = coverage_per_ac,
            total_scenarios               = total,
            estimated_coverage_percent    = float(data.get("estimated_coverage_percent", 0.0) or 0.0),
            test_data_requirements        = [str(x) for x in data.get("test_data_requirements", [])],
            environment_prerequisites     = [str(x) for x in data.get("environment_prerequisites", [])],
            entry_criteria                = [str(x) for x in data.get("entry_criteria", [])],
            exit_criteria                 = [str(x) for x in data.get("exit_criteria", [])],
            estimated_execution_time_minutes = int(data.get("estimated_execution_time_minutes", 0) or 0),
            model_used                    = model_used,
            generated_at                  = datetime.now(),
            tokens_used                   = tokens_used,
            prompt_version                = PROMPT_VERSION,
        )

    def _fallback_output(self, techniques: list[str]) -> dict:
        """Deterministic fallback when LLM call fails — returns empty-but-valid structure."""
        return {
            "techniques_used":                techniques,
            "technique_rationale":            {t: "LLM unavailable — fallback" for t in techniques},
            "scenarios":                      [],
            "decision_table":                 [],
            "pairwise_matrix":                [],
            "state_diagram":                  {},
            "coverage_per_ac":                {},
            "total_scenarios":                0,
            "estimated_coverage_percent":     0.0,
            "test_data_requirements":         [],
            "environment_prerequisites":      [],
            "entry_criteria":                 [],
            "exit_criteria":                  [],
            "estimated_execution_time_minutes": 0,
        }

    def save_report(self, output: TestPlanOutput, feature: str, run_id: str) -> dict[str, str]:
        """
        Persist test plan as JSON + Excel + CSV inside reports/test_plans/.

        Args:
            output:  TestPlanOutput to serialise.
            feature: Slugified feature name used as filename component.
            run_id:  Pipeline run ID for uniqueness.

        Returns:
            Dict with keys "json", "excel", "csv" pointing to saved files.
        """
        from skills.reporting.excel_writer import test_plan_excel_writer

        # JSON
        json_path = Path(f"reports/test_plans/{feature}_{run_id}.json")
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(output.model_dump_json(indent=2))

        # Excel + CSV
        sheet_paths = test_plan_excel_writer.write_both(output)

        paths = {
            "json":  str(json_path),
            "excel": str(sheet_paths["excel"]),
            "csv":   str(sheet_paths["csv"]),
        }
        logger.info(
            "test_plan_saved",
            path=paths["json"],
            excel=paths["excel"],
            csv=paths["csv"],
            scenarios=output.total_scenarios,
            techniques=output.techniques_used,
        )
        return paths


test_plan_agent = TestPlanAgent()
