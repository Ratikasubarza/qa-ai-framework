"""
Skill Gap Agent — Phase 9
Compares generated test cases vs acceptance criteria,
identifies untested scenarios, and outputs a coverage gap report.
"""
from __future__ import annotations
import json
import structlog
from pathlib import Path
from datetime import datetime

from core.llm_client import llm_client, ModelTier
from core.circuit_breaker import get_breaker
from core.input_sanitizer import sanitize

logger     = structlog.get_logger(__name__)
AGENT_NAME = "skill_gap_agent"

SYSTEM_PROMPT = """You are a QA coverage analyst.

Given:
- A list of acceptance criteria (AC) from a ticket
- A list of generated test cases

Your job:
1. Map each AC to the test cases that cover it
2. Identify ACs with NO test coverage
3. Identify edge cases missing from the test suite
4. Calculate coverage percentage

Respond ONLY with valid JSON:
{
  "coverage_percentage": 85.0,
  "covered_ac": ["AC-1", "AC-3"],
  "uncovered_ac": ["AC-2"],
  "missing_scenarios": [
    "Test empty state when no results found",
    "Test concurrent login attempts"
  ],
  "recommendations": [
    "Add negative test for AC-2",
    "Add performance test for search"
  ]
}"""


class SkillGapAgent:
    def __init__(self):
        self.breaker = CircuitBreaker(agent_name=AGENT_NAME)

    def analyze(
        self,
        acceptance_criteria: list[str],
        test_cases: list[dict],
        feature: str = "",
    ) -> dict:
        """
        Compare AC vs test cases, return gap analysis dict.
        """
        logger.info("skill_gap_start", feature=feature,
                    ac_count=len(acceptance_criteria),
                    tc_count=len(test_cases))

        ac_text = sanitize(
            "\n".join(f"- {ac}" for ac in acceptance_criteria),
            source="acceptance_criteria",
        ).content
        tc_text = sanitize(
            "\n".join(
                f"- [{tc.get('scenario_id','?')}] {tc.get('name', tc.get('title','?'))}"
                for tc in test_cases
            ),
            source="test_cases",
        ).content

        def _call():
            return llm_client.complete_text(
                system=SYSTEM_PROMPT,
                user=(
                    f"Feature: {feature}\n\n"
                    f"Acceptance Criteria:\n{ac_text}\n\n"
                    f"Generated Test Cases:\n{tc_text}\n\n"
                    "Analyze coverage gaps."
                ),
                tier=ModelTier.STANDARD,
                agent_name=AGENT_NAME,
                json_mode=True,
            )

        try:
            response = self.breaker.call(_call)
            raw = (response.content or "").strip()
            raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
            data = json.loads(raw)
        except Exception as e:
            logger.error("skill_gap_failed", error=str(e))
            # Deterministic fallback
            data = {
                "coverage_percentage": round(
                    len(test_cases) / max(len(acceptance_criteria), 1) * 100, 1
                ),
                "covered_ac": [],
                "uncovered_ac": acceptance_criteria,
                "missing_scenarios": [],
                "recommendations": ["Review test cases manually — LLM analysis failed"],
            }

        logger.info("skill_gap_complete",
                    coverage=data.get("coverage_percentage"),
                    gaps=len(data.get("uncovered_ac", [])))
        return data

    def save_report(self, gap_data: dict, feature: str, run_id: str) -> str:
        """Save gap report as JSON file, return path."""
        path = Path(f"reports/gap_reports/{feature}_{run_id}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "feature":    feature,
            "run_id":     run_id,
            "timestamp":  datetime.now().isoformat(),
            **gap_data,
        }
        path.write_text(json.dumps(report, indent=2))
        logger.info("gap_report_saved", path=str(path))
        return str(path)


skill_gap_agent = SkillGapAgent()