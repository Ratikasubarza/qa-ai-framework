"""
Code Generator Agent — converts TestCaseAgentOutput into runnable Playwright Python code.
Output: pytest files saved to features/{feature}/steps/
"""
import re
import structlog
from pathlib import Path
from core.llm_client import llm_client, ModelTier
from core.agent_contracts import TestCaseAgentOutput, Platform
from core.circuit_breaker import get_breaker
from core.prompt_manager import prompt_manager
from config.test_config import TestConfig

logger = structlog.get_logger(__name__)

AGENT_NAME    = "code_gen_agent"
PROMPT_NAME   = "code_gen"
PROMPT_VERSION = "1.0.0"

BASE_URLS = {
    Platform.WEB: TestConfig.WEB_APP_URL,
    Platform.API: TestConfig.API_URL,
}


class CodeGeneratorAgent:
    def __init__(self):
        self.breaker = get_breaker(AGENT_NAME)

    def run(self, test_output: TestCaseAgentOutput, platform: Platform = Platform.WEB) -> dict[str, str]:
        """
        Generate Playwright code from test case output.
        Returns dict of {filename: code_content}
        """
        logger.info(
            "code_gen_start",
            feature=test_output.feature,
            scenarios=test_output.total_scenarios,
        )

        # Format test cases for prompt
        tc_text = self._format_test_cases(test_output)

        # Load prompt
        template     = prompt_manager.get(PROMPT_NAME)
        base_url     = BASE_URLS.get(platform, BASE_URLS[Platform.WEB])
        feature_low  = test_output.feature.lower().replace(" ", "_")

        system_prompt = template.format(
            base_url=base_url,
            feature=test_output.feature,
            feature_lower=feature_low,
            platform=platform.value,
            test_cases=tc_text,
            locators_context="No existing locators — generate based on best practices.",
        )

        # LLM call
        def _call():
            return llm_client.complete_text(
                system=system_prompt,
                user=f"Generate complete Playwright Python code for: {test_output.feature}",
                tier=ModelTier.STANDARD,
                agent_name=AGENT_NAME,
                json_mode=False,
            )

        response = self.breaker.call(_call)
        files    = self._parse_files(response.content, feature_low)

        # Save files
        saved = self._save_files(files, feature_low)
        logger.info("code_gen_complete", files=list(saved.keys()))

        return saved

    def _format_test_cases(self, output: TestCaseAgentOutput) -> str:
        lines = []
        for s in output.scenarios:
            lines.append(f"Scenario ID: {s.scenario_id}")
            lines.append(f"Name: {s.name}")
            lines.append(f"Type: {s.test_type.value}")
            lines.append(f"Priority: {s.priority.value}")
            lines.append(f"Precondition: {s.precondition}")
            lines.append("Steps:")
            for step in s.steps:
                lines.append(f"  {step.step_number}. {step.action} → {step.expected}")
            lines.append(f"Expected Result: {s.expected_result}")
            if s.edge_cases:
                lines.append(f"Edge Cases: {', '.join(s.edge_cases)}")
            if s.combination_edge_cases:
                lines.append(f"Combination Edge Cases: {', '.join(s.combination_edge_cases)}")
            if s.weird_edge_cases:
                lines.append(f"Weird Edge Cases: {', '.join(s.weird_edge_cases)}")
            lines.append(f"Regression Candidate: {s.regression_candidate}")
            if s.regression_risk_area:
                lines.append(f"Regression Risk Area: {', '.join(s.regression_risk_area)}")
            lines.append("")
        return "\n".join(lines)

    def _parse_files(self, raw: str, feature_low: str) -> dict[str, str]:
        """Parse LLM output into {filename: content} dict."""
        files = {}

        # Split by file markers
        parts = re.split(r"# === FILE: (.+?) ===", raw)

        if len(parts) >= 3:
            # Has file markers
            for i in range(1, len(parts), 2):
                filename = parts[i].strip()
                content  = parts[i + 1].strip() if i + 1 < len(parts) else ""
                if content:
                    files[filename] = content
        else:
            # No markers — save as single steps file
            files[f"features/{feature_low}/steps/{feature_low}_steps.py"] = raw.strip()

        # Always ensure conftest exists
        if "conftest.py" not in files:
            files["conftest.py"] = self._default_conftest()

        return files

    def _default_conftest(self) -> str:
        return '''import pytest
from playwright.sync_api import Page
from config.test_config import TestConfig

BASE_URL = TestConfig.WEB_APP_URL

@pytest.fixture(scope="session")
def base_url():
    return BASE_URL

@pytest.fixture(autouse=True)
def navigate_to_base(page: Page, base_url: str):
    """Navigate to base URL before each test."""
    page.goto(base_url)
'''

    def _save_files(self, files: dict[str, str], feature_low: str) -> dict[str, str]:
        saved = {}
        for filename, content in files.items():
            path = Path(filename)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            saved[filename] = str(path.absolute())
            logger.info("file_saved", path=filename)
        return saved


code_generator_agent = CodeGeneratorAgent()
