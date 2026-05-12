"""
Test Case Agent Eval — automated quality gate.
Runs BEFORE human approval workflow is activated.
Compares agent output against golden fixtures.
CI blocks merge if score < threshold.
"""
import json
import pytest
from pathlib import Path
from dataclasses import dataclass
from agents.test_case_agent import test_case_agent
from core.agent_contracts import TestCaseAgentInput, Platform
from config.settings import settings

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "golden_test_cases"
THRESHOLD    = 0.85


@dataclass
class EvalResult:
    fixture_id:      str
    coverage_score:  float   # % of expected scenarios matched
    precision_score: float   # % of steps that are concrete
    has_edge_cases:  bool
    has_combination_edge_cases: bool
    has_weird_edge_cases: bool
    passed:          bool
    notes:           str = ""


def _load_fixtures() -> list[dict]:
    """Load golden fixture files from fixtures/golden_test_cases/."""
    fixtures = []
    for path in FIXTURES_DIR.glob("*.json"):
        with open(path) as f:
            fixtures.append(json.load(f))
    return fixtures


def _score_output(output, golden: dict) -> EvalResult:
    expected_count = golden.get("expected_scenario_count", 1)
    actual_count   = output.total_scenarios

    coverage = min(actual_count / expected_count, 1.0) if expected_count > 0 else 0.0

    # Check step quality — penalize vague steps
    vague_words = {"verify", "check", "ensure", "make sure", "confirm"}
    total_steps, vague_steps = 0, 0
    for scenario in output.scenarios:
        for step in scenario.steps:
            total_steps += 1
            if any(w in step.action.lower() for w in vague_words):
                vague_steps += 1

    precision = 1.0 - (vague_steps / total_steps) if total_steps > 0 else 0.0

    # Edge case coverage
    has_edge_cases = any(len(s.edge_cases) > 0 for s in output.scenarios)
    has_combination_edge_cases = any(len(s.combination_edge_cases) > 0 for s in output.scenarios)
    has_weird_edge_cases = any(len(s.weird_edge_cases) > 0 for s in output.scenarios)
    edge_score = sum([
        has_edge_cases,
        has_combination_edge_cases,
        has_weird_edge_cases,
    ]) / 3

    overall = (coverage * 0.5) + (precision * 0.3) + (0.2 * edge_score)

    return EvalResult(
        fixture_id=golden.get("id", "unknown"),
        coverage_score=round(coverage, 2),
        precision_score=round(precision, 2),
        has_edge_cases=has_edge_cases,
        has_combination_edge_cases=has_combination_edge_cases,
        has_weird_edge_cases=has_weird_edge_cases,
        passed=overall >= THRESHOLD,
        notes=f"Overall: {overall:.2f} (threshold: {THRESHOLD})",
    )


@pytest.mark.asyncio
async def test_eval_all_fixtures():
    """Run eval against all golden fixtures. Fails if any score < threshold."""
    fixtures = _load_fixtures()

    if not fixtures:
        pytest.skip("No golden fixtures found in tests/evals/fixtures/golden_test_cases/")

    # Disable approval for evals
    original_approval = settings.approval_required
    settings.approval_required = False

    results = []
    try:
        for fixture in fixtures:
            input_data = TestCaseAgentInput(
                feature=fixture["feature"],
                description=fixture["description"],
                platforms=[Platform(p) for p in fixture.get("platforms", ["web"])],
                acceptance_criteria=fixture.get("acceptance_criteria", []),
            )
            output = await test_case_agent.run(input_data)
            result = _score_output(output, fixture)
            results.append(result)

            print(f"\n[EVAL] {result.fixture_id}")
            print(f"  Coverage:  {result.coverage_score:.0%}")
            print(f"  Precision: {result.precision_score:.0%}")
            print(f"  Edge Cases: {'✓' if result.has_edge_cases else '✗'}")
            print(f"  Combination Edge Cases: {'✓' if result.has_combination_edge_cases else '✗'}")
            print(f"  Weird Edge Cases: {'✓' if result.has_weird_edge_cases else '✗'}")
            print(f"  Result:    {'PASS' if result.passed else 'FAIL'}")
    finally:
        settings.approval_required = original_approval

    failed = [r for r in results if not r.passed]
    assert not failed, (
        f"\n{len(failed)}/{len(results)} eval fixtures FAILED:\n"
        + "\n".join(f"  - {r.fixture_id}: {r.notes}" for r in failed)
    )


# ── Sample golden fixture — create this in fixtures/golden_test_cases/ ──────
SAMPLE_FIXTURE = {
    "id": "login_basic",
    "feature": "User Login",
    "description": "User authenticates with email and password",
    "platforms": ["web"],
    "acceptance_criteria": [
        "User can log in with valid credentials",
        "Login fails with invalid password",
        "Login fails with unregistered email",
        "Session persists after page refresh",
    ],
    "expected_scenario_count": 4,
}

if __name__ == "__main__":
    # Create sample fixture if none exist
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    sample_path = FIXTURES_DIR / "login_basic.json"
    if not sample_path.exists():
        with open(sample_path, "w") as f:
            json.dump(SAMPLE_FIXTURE, f, indent=2)
        print(f"Sample fixture created: {sample_path}")
