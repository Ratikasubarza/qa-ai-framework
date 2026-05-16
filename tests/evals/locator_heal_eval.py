"""
Locator Heal Eval — automated quality gate for the Locator Agent.

Checks that healed locators:
  1. Prefer stable strategies (data-testid > role > label > placeholder)
  2. Return at least 2 candidates per element
  3. First candidate is high or medium confidence

CI blocks merge if pass rate < threshold.
"""
import pytest
from dataclasses import dataclass

from agents.locator_agent import locator_agent

THRESHOLD        = 0.80
STABLE_STRATEGIES = {"data-testid", "role", "label", "placeholder"}

FIXTURES: list[dict] = [
    {
        "id":                  "login_email_field",
        "broken_locator":      "input.email-field-v2",
        "element_description": "Email input on login page",
        "dom_snapshot": (
            '<input type="email" data-testid="login-email" '
            'placeholder="Enter email" class="email-field-v2" aria-label="Email">'
        ),
        "expect_strategy": "data-testid",
    },
    {
        "id":                  "login_password_field",
        "broken_locator":      "input.password-field-old",
        "element_description": "Password input on login page",
        "dom_snapshot": (
            '<input type="password" data-testid="login-password" '
            'placeholder="Enter password" class="password-field-old">'
        ),
        "expect_strategy": "data-testid",
    },
    {
        "id":                  "login_submit_button",
        "broken_locator":      "button.btn-primary-new",
        "element_description": "Login submit button",
        "dom_snapshot": (
            '<button type="submit" data-testid="login-submit" '
            'aria-label="Log In">Log In</button>'
        ),
        "expect_strategy": "data-testid",
    },
    {
        "id":                  "register_fullname",
        "broken_locator":      "input#fullname_v3",
        "element_description": "Full name input on registration form",
        "dom_snapshot": (
            '<input type="text" placeholder="Your full name" '
            'aria-label="Full Name" class="input-primary">'
        ),
        "expect_strategy": "role",
    },
    {
        "id":                  "register_linkedin",
        "broken_locator":      ".linkedin-input-deprecated",
        "element_description": "LinkedIn URL input on registration form",
        "dom_snapshot": (
            '<input type="url" placeholder="https://linkedin.com/in/username" '
            'aria-label="LinkedIn URL" class="linkedin-input-deprecated">'
        ),
        "expect_strategy": "placeholder",
    },
]


@dataclass
class HealResult:
    fixture_id:       str
    candidates_count: int
    top_strategy:     str
    top_confidence:   str
    is_stable:        bool
    passed:           bool
    notes:            str = ""


def _evaluate_fixture(fx: dict) -> HealResult:
    candidates = locator_agent.suggest(
        broken_locator=fx["broken_locator"],
        element_description=fx["element_description"],
        dom_snapshot=fx["dom_snapshot"],
    )

    if not candidates:
        return HealResult(
            fixture_id=fx["id"],
            candidates_count=0,
            top_strategy="none",
            top_confidence="none",
            is_stable=False,
            passed=False,
            notes="Agent returned no candidates",
        )

    top          = candidates[0]
    top_strategy = top.get("strategy", "unknown")
    top_conf     = top.get("confidence", "low")
    is_stable    = top_strategy in STABLE_STRATEGIES
    enough_cands = len(candidates) >= 2
    good_conf    = top_conf in {"high", "medium"}

    passed = is_stable and enough_cands and good_conf

    return HealResult(
        fixture_id=fx["id"],
        candidates_count=len(candidates),
        top_strategy=top_strategy,
        top_confidence=top_conf,
        is_stable=is_stable,
        passed=passed,
        notes=(
            f"expected={fx['expect_strategy']} got={top_strategy} "
            f"conf={top_conf} candidates={len(candidates)}"
        ),
    )


def test_eval_locator_healing():
    """
    Locator heal quality gate.
    Each fixture must: use a stable strategy, return ≥2 candidates,
    top candidate has high|medium confidence.
    Fails if pass rate < threshold.
    """
    if not FIXTURES:
        pytest.skip("No locator heal fixtures defined")

    results = [_evaluate_fixture(fx) for fx in FIXTURES]

    for r in results:
        print(f"\n[HEAL-EVAL] {r.fixture_id}")
        print(f"  Candidates:   {r.candidates_count}")
        print(f"  Top strategy: {r.top_strategy} ({'stable' if r.is_stable else 'unstable'})")
        print(f"  Confidence:   {r.top_confidence}")
        print(f"  Result:       {'PASS' if r.passed else 'FAIL'}")
        if not r.passed:
            print(f"  Notes:        {r.notes}")

    pass_rate = sum(1 for r in results if r.passed) / len(results)
    assert pass_rate >= THRESHOLD, (
        f"Locator heal pass rate {pass_rate:.0%} below threshold {THRESHOLD:.0%}\n"
        + "\n".join(f"  FAIL {r.fixture_id}: {r.notes}" for r in results if not r.passed)
    )
