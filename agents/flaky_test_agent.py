"""
Flaky Test Agent — identifies tests that intermittently pass/fail.
Input:  List of recent test run records (test_name, outcomes, errors)
Output: FlakyTestResult classifications with root cause + remediation

Flow:
  1. Receive test history (N recent runs per test)
  2. Compute flakiness score (alternation rate in pass/fail sequence)
  3. Call LLM for root cause classification per flaky test
  4. Return list ranked by flakiness score descending
"""
import json
import structlog
from dataclasses import dataclass, field
from core.llm_client import llm_client, ModelTier
from core.circuit_breaker import get_breaker
from core import input_sanitizer

logger = structlog.get_logger(__name__)

AGENT_NAME = "flaky_test_agent"

ANALYSIS_PROMPT = """You are a Senior QA Engineer specializing in test reliability.
Analyze this flaky test and identify the root cause.

TEST NAME: {test_name}
FLAKINESS SCORE: {flakiness_score:.0%} ({failure_count}/{total_runs} failures)
RECENT OUTCOMES (newest first): {outcomes}
ERROR PATTERNS:
{error_patterns}

FLAKINESS CATEGORIES:
1. timing          — race condition, async not awaited, sleep too short
2. data_dependency — test depends on shared/leftover state from another test
3. external_service — network, API rate limit, third-party instability
4. locator         — UI element locator brittle or timing-dependent
5. environment     — CI vs local discrepancy, resource contention
6. test_order      — test assumes previous test ran first
7. genuine_bug     — real product instability causes intermittent failure

INTEGRITY RULES — NON-NEGOTIABLE:
- If category is "genuine_bug": remediation MUST describe the developer-side fix needed
  (e.g., "Fix race condition in session invalidation on PUT /v1/users/me/password").
  NEVER suggest: removing the assertion, skipping the test, weakening expected values,
  catching the exception, or marking xfail to hide a product defect.
  The test is working correctly — the product code is broken.
- If confidence is "low" and you cannot determine the cause: set category to "genuine_bug"
  and root_cause to "Insufficient history to determine cause with confidence — treat as
  product instability until confirmed otherwise."
- Do NOT invent root causes. Only state what the error patterns directly support.
- quarantine_recommended must be false when category is "genuine_bug" — quarantining
  a test that catches a real bug silently hides the defect from the team.

OUTPUT FORMAT: Return ONLY valid JSON, no preamble:
{{
  "category": "<one of the 7 categories>",
  "confidence": "high|medium|low",
  "root_cause": "<1-2 sentence specific explanation>",
  "remediation": "<exact fix: what to change in the test or product code>",
  "quarantine_recommended": <true|false>
}}
"""


@dataclass
class FlakyTestResult:
    test_name:              str
    flakiness_score:        float       # 0.0–1.0, higher = more flaky
    failure_count:          int
    total_runs:             int
    category:               str
    confidence:             str
    root_cause:             str
    remediation:            str
    quarantine_recommended: bool
    error_patterns:         list[str] = field(default_factory=list)


class FlakyTestAgent:
    def __init__(self):
        self.breaker = get_breaker(AGENT_NAME)

    def _compute_flakiness_score(self, outcomes: list[str]) -> float:
        """
        Alternation rate: how often outcome flips between consecutive runs.
        Always-pass or always-fail → 0.0.  Every-other-run flip → 1.0.
        """
        if len(outcomes) < 2:
            return 0.0
        transitions = sum(1 for a, b in zip(outcomes, outcomes[1:]) if a != b)
        return transitions / (len(outcomes) - 1)

    def _dedupe_errors(self, errors: list[str]) -> list[str]:
        seen, patterns = set(), []
        for e in errors:
            key = (e or "")[:80]
            if key not in seen:
                seen.add(key)
                patterns.append((e or "")[:200])
        return patterns[:5]

    def analyze(
        self,
        test_name: str,
        outcomes:  list[str],       # "PASS" | "FAIL" ordered oldest→newest
        errors:    list[str] | None = None,
    ) -> "FlakyTestResult | None":
        """
        Analyze one test's run history. Returns None if the test is stable.
        Stable means: always passes, always fails, or fewer than 3 runs total.
        """
        failure_count = outcomes.count("FAIL")
        total_runs    = len(outcomes)

        if total_runs < 3 or failure_count == 0 or failure_count == total_runs:
            return None

        flakiness_score = self._compute_flakiness_score(outcomes)
        error_patterns  = self._dedupe_errors(errors or [])

        clean_name = input_sanitizer.sanitize(test_name, source="test_name")

        prompt = ANALYSIS_PROMPT.format(
            test_name=clean_name.content,
            flakiness_score=flakiness_score,
            failure_count=failure_count,
            total_runs=total_runs,
            outcomes=" → ".join(outcomes[-10:]),
            error_patterns=json.dumps(error_patterns, indent=2),
        )

        def _call():
            return llm_client.complete_text(
                system=prompt,
                user=f"Classify flakiness for: {clean_name.content}",
                tier=ModelTier.FAST,
                agent_name=AGENT_NAME,
                json_mode=True,
            )

        try:
            response = self.breaker.call(_call)
            raw  = (response.content or "").strip()
            raw  = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
            data = json.loads(raw)

            category = data.get("category", "unknown")

            # Programmatic safety: genuine product bugs must never be quarantined.
            # Quarantine hides a real defect from the team.
            quarantine = bool(data.get("quarantine_recommended", False))
            if category == "genuine_bug":
                quarantine = False

            result = FlakyTestResult(
                test_name=test_name,
                flakiness_score=round(flakiness_score, 3),
                failure_count=failure_count,
                total_runs=total_runs,
                category=category,
                confidence=data.get("confidence", "low"),
                root_cause=data.get("root_cause", ""),
                remediation=data.get("remediation", ""),
                quarantine_recommended=quarantine,
                error_patterns=error_patterns,
            )
            logger.info(
                "flaky_test_analyzed",
                test=test_name,
                score=result.flakiness_score,
                category=result.category,
                quarantine=result.quarantine_recommended,
            )
            return result
        except Exception as e:
            logger.error("flaky_test_agent_failed", test=test_name, error=str(e))
            raise

    def analyze_batch(
        self,
        test_history:        list[dict],
        flakiness_threshold: float = 0.20,
    ) -> list[FlakyTestResult]:
        """
        Analyze multiple tests. Each dict must contain:
          test_name: str
          outcomes:  list[str]   # "PASS" | "FAIL"
          errors:    list[str]   # optional — error messages for FAIL runs

        Returns only tests with flakiness_score >= threshold,
        sorted by score descending (most flaky first).
        """
        results = []
        for entry in test_history:
            name     = entry.get("test_name", "unknown")
            outcomes = entry.get("outcomes", [])
            errors   = entry.get("errors", [])
            try:
                result = self.analyze(name, outcomes, errors)
                if result and result.flakiness_score >= flakiness_threshold:
                    results.append(result)
            except Exception as e:
                logger.warning("flaky_analysis_skipped", test=name, error=str(e))

        results.sort(key=lambda r: r.flakiness_score, reverse=True)
        logger.info(
            "flaky_batch_complete",
            total=len(test_history),
            flaky=len(results),
            threshold=flakiness_threshold,
        )
        return results


flaky_test_agent = FlakyTestAgent()
