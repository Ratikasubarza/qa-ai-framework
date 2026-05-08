"""
Locator Agent — suggests new locators when existing ones break.
Uses LLM to analyze DOM snapshot and suggest 3 candidate locators
ordered by stability (data-testid first, role second, etc.)
"""
import json
import structlog
from core.llm_client import llm_client, ModelTier
from core.circuit_breaker import get_breaker
from core import input_sanitizer

logger = structlog.get_logger(__name__)

AGENT_NAME = "locator_agent"

SYSTEM_PROMPT = """You are a Senior QA Engineer expert in Playwright locator strategies.
A UI element locator has broken. Analyze the DOM snapshot and suggest 3 alternative locators.

BROKEN LOCATOR: {broken_locator}
ELEMENT DESCRIPTION: {element_description}
DOM SNAPSHOT (relevant section):
{dom_snapshot}

LOCATOR PRIORITY (most stable to least stable):
1. [data-testid="..."] — most stable, ask devs to add if missing
2. page.get_by_role("...", name="...") — semantic, good stability
3. page.get_by_label("...") — for form inputs
4. page.get_by_placeholder("...") — for inputs with placeholder
5. input[type="email/password/submit"] — attribute-based
6. button[type="submit"] — specific attribute
7. CSS class — least stable, last resort

OUTPUT FORMAT: Return ONLY valid JSON, no preamble:
{{
  "candidates": [
    {{
      "locator": "string — exact Playwright locator",
      "strategy": "data-testid|role|label|placeholder|attribute|css",
      "confidence": "high|medium|low",
      "reasoning": "why this locator should work"
    }}
  ],
  "recommendation": "string — which candidate to try first and why"
}}
"""


class LocatorAgent:
    def __init__(self):
        self.breaker = get_breaker(AGENT_NAME)

    def suggest(
        self,
        broken_locator:     str,
        element_description: str,
        dom_snapshot:       str,
    ) -> list[dict]:
        """
        Suggest 3 candidate locators for a broken element.
        Returns list of candidates ordered by confidence.
        """
        clean_dom = input_sanitizer.sanitize(dom_snapshot, source="dom_snapshot")

        system = SYSTEM_PROMPT.format(
            broken_locator=broken_locator,
            element_description=element_description,
            dom_snapshot=clean_dom.content[:3000],
        )

        def _call():
            return llm_client.complete_text(
                system=system,
                user=f"Suggest locators for broken element: {element_description}",
                tier=ModelTier.FAST,
                agent_name=AGENT_NAME,
                json_mode=True,
            )

        try:
            response = self.breaker.call(_call)
            data     = json.loads(response.content)
            candidates = data.get("candidates", [])
            logger.info(
                "locator_candidates_generated",
                element=element_description,
                count=len(candidates),
            )
            return candidates
        except Exception as e:
            logger.error("locator_agent_failed", error=str(e))
            return []


locator_agent = LocatorAgent()
