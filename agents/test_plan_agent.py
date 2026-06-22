"""
Test Plan Agent — intelligently selects testing techniques per AC using LLM reasoning.

Both black box and grey box techniques are considered.
Technique selection is driven per-AC by LLM analysis, not by keyword matching.

Black box:  equivalence_partitioning, boundary_value_analysis, decision_table,
            state_transition, pairwise_testing, use_case_testing, error_guessing
Grey box:   api_contract_testing, db_state_validation, rule_engine_validation,
            integration_testing, side_effect_verification
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
    ACTechniqueMapping, RiskItem,
)
from core.circuit_breaker import get_breaker
from core.input_sanitizer import sanitize

logger = structlog.get_logger(__name__)

AGENT_NAME     = "test_plan_agent"
PROMPT_VERSION = "2.0.0"

# Full technique taxonomy — passed to LLM so it can reason which to apply
_TECHNIQUE_TAXONOMY = {
    "black_box": {
        "equivalence_partitioning": (
            "Test representative values from valid and invalid input partitions. "
            "Apply when AC describes valid/invalid input ranges or user categories."
        ),
        "boundary_value_analysis": (
            "Test min, min+1, nominal, max-1, max, and off-by-one values. "
            "Apply when AC has numeric ranges, character limits, time thresholds, or quotas."
        ),
        "decision_table": (
            "Test all combinations of interacting boolean/categorical conditions. "
            "Apply when AC has multiple conditions connected by AND/OR that produce different outcomes."
        ),
        "state_transition": (
            "Test valid transitions and invalid/blocked transitions in a stateful workflow. "
            "Apply when AC describes status changes: pending→approved, active→suspended, etc."
        ),
        "pairwise_testing": (
            "Reduce combinatorial explosion by testing all pairs of independent parameters. "
            "Apply when AC involves 3+ independent configurable parameters (platform, role, plan type, region)."
        ),
        "use_case_testing": (
            "Test complete user journeys end-to-end. "
            "Apply when AC describes a user goal spanning multiple steps or screens."
        ),
        "error_guessing": (
            "Test common failure modes: null/empty input, special characters, concurrent actions, "
            "session expiry mid-flow, network drop, duplicate submission, max+1 values. "
            "Always apply as secondary technique."
        ),
    },
    "grey_box": {
        "api_contract_testing": (
            "Verify endpoint schema, HTTP status codes (200/400/401/403/404/422/500), "
            "response time, required headers, and auth token handling. "
            "Apply when AC mentions an API endpoint, response payload, or HTTP behavior."
        ),
        "db_state_validation": (
            "Verify correct database state after operations: records created/updated/deleted, "
            "foreign keys intact, no orphaned records, audit fields populated. "
            "Apply when AC says 'saved', 'recorded', 'persisted', 'updated in database'."
        ),
        "rule_engine_validation": (
            "Verify business rules, configuration-driven behavior, and flag conditions. "
            "Apply when AC involves configurable rules, scoring engines, risk flags, or policy enforcement."
        ),
        "integration_testing": (
            "Verify correct data flow and contracts between services or layers (BE↔FE, BE↔DB, service↔service). "
            "Apply when AC describes a cross-service or cross-layer interaction."
        ),
        "side_effect_verification": (
            "Verify secondary outcomes: audit logs written, notifications sent, background jobs triggered, "
            "cache invalidated, event published. "
            "Apply when AC mentions blacklisting, notifications, audit trails, or async operations."
        ),
    },
}


class TestPlanAgent:
    """
    Generates a structured test plan by reasoning over each AC to determine
    the appropriate black box and grey box testing techniques.

    Usage:
        agent = TestPlanAgent()
        output = agent.create_test_plan({
            "feature_name": "User Login",
            "ticket_id": "HM-42",
            "acceptance_criteria": ["..."],
            "description": "...",
            "platforms": ["api", "web", "mobile"],
        })
    """

    def __init__(self) -> None:
        self.breaker = get_breaker(AGENT_NAME)

    def create_test_plan(self, requirements: dict) -> TestPlanOutput:
        feature_name = requirements.get("feature_name", "")
        ticket_id    = requirements.get("ticket_id", "")
        logger.info(
            "test_plan_agent_start",
            feature=feature_name,
            ticket=ticket_id,
            ac_count=len(requirements.get("acceptance_criteria", [])),
        )
        output = self._generate(requirements)
        logger.info(
            "test_plan_complete",
            feature=feature_name,
            black_box=output.techniques_used,
            grey_box=output.grey_box_techniques,
            scenarios=output.total_scenarios,
            coverage=output.estimated_coverage_percent,
        )
        return output

    # ── Prompt construction ────────────────────────────────────────────────────

    def _build_prompt(self, requirements: dict) -> str:
        feature_name = sanitize(requirements.get("feature_name", ""), source="feature_name").content
        ticket_id    = sanitize(requirements.get("ticket_id", ""), source="ticket_id").content
        description  = sanitize(requirements.get("description", "")[:1500], source="description").content
        platforms    = ", ".join(requirements.get("platforms", ["web"]))

        ac_lines = "\n".join(
            f"- [{i+1}] {sanitize(ac, source='ac').content}"
            for i, ac in enumerate(requirements.get("acceptance_criteria", []))
        ) or "Not provided"

        # Build taxonomy block for prompt
        bb_block = "\n".join(
            f"  {name}: {desc}"
            for name, desc in _TECHNIQUE_TAXONOMY["black_box"].items()
        )
        gb_block = "\n".join(
            f"  {name}: {desc}"
            for name, desc in _TECHNIQUE_TAXONOMY["grey_box"].items()
        )

        # JSON output template
        json_template = (
            "{{\n"
            '  "test_objective": "2-3 sentences: what this test plan verifies and why it matters",\n'
            '  "ac_technique_mapping": [\n'
            "    {{\n"
            '      "ac_id": "AC-001",\n'
            '      "ac_summary": "short summary of the AC",\n'
            '      "primary_technique": "decision_table",\n'
            '      "secondary_techniques": ["error_guessing"],\n'
            '      "grey_box_techniques": ["api_contract_testing", "db_state_validation"],\n'
            '      "why": "explain why each chosen technique fits this specific AC",\n'
            '      "estimated_test_count": 8,\n'
            '      "risk_level": "high"\n'
            "    }}\n"
            "  ],\n"
            '  "techniques_used": ["decision_table", "equivalence_partitioning", "error_guessing"],\n'
            '  "grey_box_techniques": ["api_contract_testing"],\n'
            '  "technique_rationale": {{"decision_table": "why chosen overall"}},\n'
            '  "scenarios": [\n'
            "    {{\n"
            '      "scenario_id": "TC-001",\n'
            '      "scenario_name": "descriptive name",\n'
            '      "technique": "decision_table",\n'
            '      "type": "happy_path|negative|edge_case|boundary|state_transition|integration",\n'
            '      "priority": "P1|P2|P3",\n'
            '      "platforms": ["api", "web", "mobile"],\n'
            '      "preconditions": ["user is registered and verified"],\n'
            '      "inputs": {{"field": "value"}},\n'
            '      "expected_outcome": "exact expected result including HTTP status / DB state if grey box",\n'
            '      "risk_level": "high|medium|low",\n'
            '      "tags": ["smoke", "regression", "api_contract"]\n'
            "    }}\n"
            "  ],\n"
            '  "decision_table": [{{"condition": "utilization_rate >= 97%", "rules": ["Y", "N", "Y"]}}],\n'
            '  "pairwise_matrix": [],\n'
            '  "state_diagram": {{"states": [], "transitions": [], "invalid_transitions": []}},\n'
            '  "risk_matrix": [\n'
            "    {{\n"
            '      "risk_area": "authentication bypass",\n'
            '      "probability": "low",\n'
            '      "impact": "high",\n'
            '      "severity": "high",\n'
            '      "mitigation": "verify token validation on every protected endpoint"\n'
            "    }}\n"
            "  ],\n"
            '  "coverage_per_ac": {{"AC-001": 90.0}},\n'
            '  "total_scenarios": 0,\n'
            '  "estimated_coverage_percent": 0,\n'
            '  "test_data_requirements": ["approved user account", "staging DB accessible"],\n'
            '  "environment_prerequisites": ["feature deployed to staging"],\n'
            '  "entry_criteria": ["all AC have been reviewed and signed off"],\n'
            '  "exit_criteria": ["all P1 scenarios passed", "coverage >= 90%"],\n'
            '  "estimated_execution_time_minutes": 0\n'
            "}}"
        )

        return (
            "You are a Senior QA Engineer / SDET with 10+ years experience.\n"
            "Create a comprehensive test plan by reasoning over EACH acceptance criterion\n"
            "to determine the correct testing techniques.\n\n"
            f"Feature: {feature_name}\n"
            f"Ticket: {ticket_id}\n"
            f"Target Platforms: {platforms}\n"
            f"Description: {description}\n\n"
            f"Acceptance Criteria:\n{ac_lines}\n\n"
            "── TESTING TECHNIQUE TAXONOMY ──────────────────────────────────────────\n"
            "BLACK BOX techniques (test from the outside, no internal knowledge needed):\n"
            f"{bb_block}\n\n"
            "GREY BOX techniques (test with knowledge of internals: API, DB, rules engine):\n"
            f"{gb_block}\n\n"
            "── TECHNIQUE SELECTION RULES ────────────────────────────────────────────\n"
            "For EACH AC, independently determine:\n"
            "1. primary_technique: the single best technique for this AC\n"
            "2. secondary_techniques: additional black box techniques (always include error_guessing)\n"
            "3. grey_box_techniques: applicable grey box techniques based on what the AC touches\n"
            "4. why: explicit reasoning — WHY this technique fits, and WHY others do NOT\n"
            "5. risk_level: high if involves payment/auth/data-loss/blacklist/security; else medium/low\n\n"
            "For scenarios:\n"
            "- decision_table: generate one scenario per unique condition combination row\n"
            "- boundary_value_analysis: generate scenarios for min-1, min, min+1, nominal, max-1, max, max+1\n"
            "- state_transition: generate one scenario per valid transition + key invalid transitions\n"
            "- pairwise_testing: generate minimal set covering all parameter pairs\n"
            "- api_contract_testing: include HTTP status, response schema, auth header verification\n"
            "- db_state_validation: include explicit DB state check in expected_outcome\n"
            "- side_effect_verification: verify audit log / notification / background job in expected_outcome\n\n"
            "Output ONLY valid JSON. No markdown. No explanation outside JSON.\n"
            f"Format:\n{json_template}"
        )

    # ── LLM call & parsing ─────────────────────────────────────────────────────

    def _generate(self, requirements: dict) -> TestPlanOutput:
        feature_name  = requirements.get("feature_name", "")
        ticket_id     = requirements.get("ticket_id", "")
        system_prompt = self._build_prompt(requirements)
        model_used    = "unknown"
        tokens_used   = 0

        def _call():
            return llm_client.complete_text(
                system=system_prompt,
                user=f"Generate comprehensive test plan for: {feature_name} (Ticket: {ticket_id})",
                tier=ModelTier.COMPLEX,
                agent_name=AGENT_NAME,
                json_mode=True,
            )

        try:
            response    = self.breaker.call(_call)
            model_used  = response.model
            tokens_used = response.tokens_used
            raw         = (response.content or "").strip()
            raw         = re.sub(r"^```json", "", raw).strip()
            raw         = re.sub(r"```$",     "", raw).strip()
            data        = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("test_plan_json_parse_failed", feature=feature_name, error=str(e))
            data = self._fallback_output(requirements)
        except Exception as e:
            logger.error("test_plan_llm_failed", feature=feature_name, error=str(e))
            data = self._fallback_output(requirements)

        return self._parse_output(data, requirements, model_used, tokens_used)

    def _parse_output(
        self,
        data:         dict,
        requirements: dict,
        model_used:   str,
        tokens_used:  int,
    ) -> TestPlanOutput:
        feature_name = requirements.get("feature_name", "")
        ticket_id    = requirements.get("ticket_id", "")

        # ── AC technique mapping ──────────────────────────────────────────────
        ac_mappings: list[ACTechniqueMapping] = []
        for item in data.get("ac_technique_mapping", []):
            if not isinstance(item, dict):
                continue
            try:
                ac_mappings.append(ACTechniqueMapping(
                    ac_id=item.get("ac_id", "AC-?"),
                    ac_summary=item.get("ac_summary", ""),
                    primary_technique=item.get("primary_technique", "equivalence_partitioning"),
                    secondary_techniques=[str(t) for t in item.get("secondary_techniques", [])],
                    grey_box_techniques=[str(t) for t in item.get("grey_box_techniques", [])],
                    why=item.get("why", ""),
                    estimated_test_count=int(item.get("estimated_test_count", 0) or 0),
                    risk_level=item.get("risk_level", "medium"),
                ))
            except Exception as e:
                logger.warning("ac_mapping_parse_error", item=item, error=str(e))

        # ── Scenarios ─────────────────────────────────────────────────────────
        _valid_types = {"happy_path","negative","edge_case","boundary","state_transition","integration"}
        _valid_prio  = {"P1","P2","P3"}
        _valid_risk  = {"high","medium","low"}

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
            except Exception as e:
                logger.warning("test_plan_scenario_parse_error", index=i, error=str(e))

        # ── Decision table ────────────────────────────────────────────────────
        dt_rows: list[DecisionTableRow] = []
        for row in data.get("decision_table", []):
            if isinstance(row, dict) and "condition" in row:
                dt_rows.append(DecisionTableRow(
                    condition=str(row.get("condition", "")),
                    rules=[str(r) for r in row.get("rules", [])],
                ))

        # ── Pairwise matrix ───────────────────────────────────────────────────
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

        # ── Risk matrix ───────────────────────────────────────────────────────
        risk_matrix: list[RiskItem] = []
        for item in data.get("risk_matrix", []):
            if not isinstance(item, dict) or "risk_area" not in item:
                continue
            try:
                risk_matrix.append(RiskItem(
                    risk_area   = str(item.get("risk_area", "")),
                    probability = item.get("probability", "medium"),
                    impact      = item.get("impact", "medium"),
                    severity    = item.get("severity", "medium"),
                    mitigation  = item.get("mitigation", ""),
                ))
            except Exception as e:
                logger.warning("risk_item_parse_error", item=item, error=str(e))

        # ── Coverage per AC ───────────────────────────────────────────────────
        coverage_per_ac: dict[str, float] = {}
        for k, v in (data.get("coverage_per_ac") or {}).items():
            try:
                coverage_per_ac[str(k)] = float(v)
            except (TypeError, ValueError):
                pass

        total = len(scenarios)

        return TestPlanOutput(
            feature_name                     = feature_name,
            ticket_id                        = ticket_id,
            test_objective                   = data.get("test_objective", ""),
            ac_technique_mapping             = ac_mappings,
            techniques_used                  = data.get("techniques_used", []),
            grey_box_techniques              = data.get("grey_box_techniques", []),
            technique_rationale              = data.get("technique_rationale", {}),
            scenarios                        = scenarios,
            decision_table                   = dt_rows,
            pairwise_matrix                  = pw_rows,
            state_diagram                    = data.get("state_diagram", {}),
            risk_matrix                      = risk_matrix,
            coverage_per_ac                  = coverage_per_ac,
            total_scenarios                  = total,
            estimated_coverage_percent       = float(data.get("estimated_coverage_percent", 0.0) or 0.0),
            test_data_requirements           = [str(x) for x in data.get("test_data_requirements", [])],
            environment_prerequisites        = [str(x) for x in data.get("environment_prerequisites", [])],
            entry_criteria                   = [str(x) for x in data.get("entry_criteria", [])],
            exit_criteria                    = [str(x) for x in data.get("exit_criteria", [])],
            estimated_execution_time_minutes = int(data.get("estimated_execution_time_minutes", 0) or 0),
            model_used                       = model_used,
            generated_at                     = datetime.now(),
            tokens_used                      = tokens_used,
            prompt_version                   = PROMPT_VERSION,
        )

    def _fallback_output(self, requirements: dict) -> dict:
        """Deterministic fallback when LLM call fails."""
        bb = list(_TECHNIQUE_TAXONOMY["black_box"].keys())
        gb = list(_TECHNIQUE_TAXONOMY["grey_box"].keys())
        return {
            "test_objective":                "LLM unavailable — fallback output",
            "ac_technique_mapping":          [],
            "techniques_used":               bb[:3],
            "grey_box_techniques":           [],
            "technique_rationale":           {t: "LLM unavailable" for t in bb[:3]},
            "scenarios":                     [],
            "decision_table":                [],
            "pairwise_matrix":               [],
            "state_diagram":                 {},
            "risk_matrix":                   [],
            "coverage_per_ac":               {},
            "total_scenarios":               0,
            "estimated_coverage_percent":    0.0,
            "test_data_requirements":        [],
            "environment_prerequisites":     [],
            "entry_criteria":                [],
            "exit_criteria":                 [],
            "estimated_execution_time_minutes": 0,
        }

    def save_report(self, output: TestPlanOutput, feature: str, run_id: str) -> dict[str, str]:
        from skills.reporting.excel_writer import test_plan_excel_writer

        json_path = Path(f"reports/test_plans/{feature}_{run_id}.json")
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(output.model_dump_json(indent=2))

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
            black_box=output.techniques_used,
            grey_box=output.grey_box_techniques,
        )
        return paths


test_plan_agent = TestPlanAgent()
