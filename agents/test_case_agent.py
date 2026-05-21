"""
Test Case Agent — Phase 2 core agent.
Input:  TestCaseAgentInput (feature + description + platforms + AC)
Output: TestCaseAgentOutput (typed, validated, provenance-tagged)
Flow:
  1. Sanitize input
  2. Retrieve RAG context
  3. Format prompt
  4. Call LLM via circuit breaker
  5. Parse + validate typed output
  6. Send to Telegram for Human-in-the-Loop approval
  7. Wait for decision
  8. Return approved output or raise on reject
"""
import json
import re
import structlog
from datetime import datetime
from core.llm_client import llm_client, ModelTier
from core.agent_contracts import (
    TestCaseAgentInput, TestCaseAgentOutput,
    ScenarioSchema, TestStep,
    TestType, Platform, Priority,
    AgentFeedback, Decision,
)
from core.circuit_breaker import get_breaker
from core import input_sanitizer
from core.prompt_manager import prompt_manager
from knowledge_base.rag_engine import rag_engine
from core.workflows.approval_workflow import review_queue
from config.settings import settings
from integrations.jira_client.jira_client import jira_client
from integrations.confluence_client.confluence_client import ConfluenceClient
import asyncio

logger = structlog.get_logger(__name__)

AGENT_NAME    = "test_case_agent"
PROMPT_NAME   = "test_case_gen"
PROMPT_VERSION = "2.0.0"
MAX_AC_PER_BATCH = 8


def _extract_json_object(raw: str) -> str:
    json_start = raw.find("{")
    json_end = raw.rfind("}")
    if json_start != -1 and json_end != -1 and json_end > json_start:
        return raw[json_start:json_end + 1].strip()
    if json_start != -1:
        return raw[json_start:].strip()
    return raw.strip()


def _salvage_scenarios_from_truncated_json(raw: str, feature: str) -> dict:
    scenarios_key = re.search(r'"(?:scenarios|test_cases|cases|testcases)"\s*:\s*\[', raw)
    if not scenarios_key:
        return {
            "feature": feature,
            "scenarios": [],
            "coverage_summary": "JSON truncated — retry",
        }

    decoder = json.JSONDecoder()
    index = scenarios_key.end()
    scenarios = []

    while index < len(raw):
        while index < len(raw) and raw[index] in " \n\r\t,":
            index += 1
        if index >= len(raw) or raw[index] == "]":
            break
        if raw[index] != "{":
            index += 1
            continue

        try:
            scenario, next_index = decoder.raw_decode(raw, index)
        except json.JSONDecodeError:
            break
        if isinstance(scenario, dict):
            scenarios.append(scenario)
        index = next_index

    return {
        "feature": feature,
        "scenarios": scenarios,
        "coverage_summary": (
            "Recovered complete scenarios from truncated JSON."
            if scenarios
            else "JSON truncated — retry"
        ),
        "parse_warnings": ["json_truncated"],
    }


class TestCaseAgent:
    def __init__(self):
        self.breaker = get_breaker(AGENT_NAME)
        self._telegram = None  # Injected lazily to avoid circular import

    @property
    def telegram(self):
        if self._telegram is None:
            from core.telegram_bot import telegram_bot
            self._telegram = telegram_bot
            self._telegram.set_review_queue(review_queue)
        return self._telegram

    async def run(
        self,
        input_data: TestCaseAgentInput,
        require_approval: bool | None = None,
    ) -> TestCaseAgentOutput:
        """Main entry point — full agent pipeline with Human-in-the-Loop."""
        logger.info(
            "test_case_agent_start",
            feature=input_data.feature,
            platforms=[p.value for p in input_data.platforms],
        )

        # ── Step 1: Sanitize ──────────────────────────────────
        clean_desc = input_sanitizer.sanitize(
            input_data.description,
            source=f"feature/{input_data.feature}"
        )
        clean_ac = [
            input_sanitizer.sanitize(ac, source="acceptance_criteria").content
            for ac in input_data.acceptance_criteria
        ]

        # ── Step 1b: Enrich from Jira (if issue key provided) ─
        jira_context_parts: list[str] = []
        if input_data.jira_story_key:
            try:
                issue = jira_client.get_issue(input_data.jira_story_key)
                logger.info("jira_issue_fetched", key=input_data.jira_story_key)

                # Merge acceptance criteria from Jira description if not supplied
                if not clean_ac and issue.get("acceptance_criteria"):
                    clean_ac = [
                        input_sanitizer.sanitize(ac, source="jira_ac").content
                        for ac in issue["acceptance_criteria"]
                    ]

                # Build Jira context block
                jira_ctx_lines = [
                    f"JIRA STORY: {issue['key']} — {input_sanitizer.sanitize(issue['summary'], source='jira_summary').content}",
                    f"Status: {issue.get('status', '')}  Priority: {issue.get('priority', '')}",
                ]
                if issue.get("description"):
                    jira_ctx_lines.append(f"Description:\n{input_sanitizer.sanitize(issue['description'][:600], source='jira_description').content}")

                # Include existing QA subtasks to avoid duplicating already-generated cases
                existing_subtasks = [
                    st for st in issue.get("subtasks", [])
                    if "QA" in st.get("summary", "").upper() or "qa-automation" in st.get("summary", "").lower()
                ]
                if existing_subtasks:
                    jira_ctx_lines.append("\nExisting QA subtasks (avoid duplicating these):")
                    for st in existing_subtasks:
                        clean_st_summary = input_sanitizer.sanitize(st['summary'], source='jira_subtask_summary').content
                        clean_st_desc = input_sanitizer.sanitize(st['description'][:200], source='jira_subtask_desc').content if st.get("description") else ""
                        jira_ctx_lines.append(
                            f"  [{st['key']}] {clean_st_summary} ({st['status']})"
                            + (f"\n    {clean_st_desc}" if clean_st_desc else "")
                        )

                jira_context_parts.append("\n".join(jira_ctx_lines))
            except Exception as e:
                logger.warning("jira_fetch_failed", key=input_data.jira_story_key, error=str(e))

        # ── Step 1c: Fetch PRD from Confluence (if URL provided) ─
        if input_data.confluence_page_url:
            try:
                confluence = ConfluenceClient()
                prd_text = confluence.fetch_page(input_data.confluence_page_url)
                if prd_text:
                    prd_clean = input_sanitizer.sanitize(prd_text[:1500], source="confluence_prd").content
                    jira_context_parts.append(
                        f"CONFLUENCE PRD:\n{prd_clean}"
                    )
                    logger.info("confluence_prd_fetched", url=input_data.confluence_page_url)
            except PermissionError:
                logger.warning("confluence_permission_denied", url=input_data.confluence_page_url)
            except FileNotFoundError:
                logger.warning("confluence_page_not_found", url=input_data.confluence_page_url)
            except Exception as e:
                logger.warning("confluence_fetch_failed", url=input_data.confluence_page_url, error=str(e))

        # Merge any extra context provided by caller
        extra_context_parts = []
        if input_data.context:
            extra_context_parts.append(input_sanitizer.sanitize(input_data.context, source="extra_context").content)
        extra_context_parts.extend(jira_context_parts)
        enriched_context = "\n\n---\n".join(extra_context_parts) if extra_context_parts else ""

        # ── Step 2: RAG retrieval ─────────────────────────────
        past_context = rag_engine.retrieve(
            query=f"{input_data.feature} {input_data.description}",
            top_k=5,
        )
        if enriched_context:
            past_context = f"{enriched_context}\n\n---\n{past_context}" if past_context else enriched_context

        # ── Step 3: Format prompt ─────────────────────────────
        if len(clean_ac) > MAX_AC_PER_BATCH:
            output = self._run_chunked_generation(
                input_data=input_data,
                clean_description=clean_desc.content,
                clean_acceptance_criteria=clean_ac,
                past_context=past_context,
            )
        else:
            output = self._run_single_generation(
                input_data=input_data,
                clean_description=clean_desc.content,
                clean_acceptance_criteria=clean_ac,
                past_context=past_context,
            )

        # ── Step 6: Human-in-the-Loop (if required) ───────────
        if require_approval is None:
            require_approval = settings.approval_required

        if require_approval:
            output = await self._request_approval(output)

        return output

    def _run_single_generation(
        self,
        input_data: TestCaseAgentInput,
        clean_description: str,
        clean_acceptance_criteria: list[str],
        past_context: str,
        batch_index: int | None = None,
        batch_total: int | None = None,
    ) -> TestCaseAgentOutput:
        template = prompt_manager.get(PROMPT_NAME)
        ac_text = "\n".join(f"- {ac}" for ac in clean_acceptance_criteria) or "Not provided"
        platforms = ", ".join(p.value for p in input_data.platforms)
        system_prompt = template.format(
            feature=input_data.feature,
            description=clean_description,
            platforms=platforms,
            acceptance_criteria=ac_text,
            past_context=past_context,
            date=__import__('datetime').datetime.now().strftime('%Y%m%d'),
        )
        batch_note = ""
        if batch_index is not None and batch_total is not None:
            batch_note = (
                f"\nThis is batch {batch_index}/{batch_total}. "
                "Generate 1-3 high-value scenarios per AC in this batch. "
                "Keep JSON complete and valid; do not cover ACs outside this batch."
            )

        def _call_llm():
            return llm_client.complete_text(
                system=system_prompt,
                user=f"Generate comprehensive test cases for: {input_data.feature}.{batch_note}",
                tier=ModelTier.STANDARD,
                agent_name=AGENT_NAME,
                json_mode=True,
            )

        response = self.breaker.call(_call_llm)
        return self._parse_output(
            response.content,
            input_data,
            response.model,
            tokens_used=response.tokens_used,
        )

    def _run_chunked_generation(
        self,
        input_data: TestCaseAgentInput,
        clean_description: str,
        clean_acceptance_criteria: list[str],
        past_context: str,
    ) -> TestCaseAgentOutput:
        chunks = [
            clean_acceptance_criteria[i:i + MAX_AC_PER_BATCH]
            for i in range(0, len(clean_acceptance_criteria), MAX_AC_PER_BATCH)
        ]
        logger.info(
            "test_case_chunked_generation",
            chunks=len(chunks),
            acceptance_criteria=len(clean_acceptance_criteria),
        )

        merged_scenarios: list[ScenarioSchema] = []
        coverage_parts: list[str] = []
        models: list[str] = []
        tokens_used = 0

        for index, chunk in enumerate(chunks, 1):
            logger.info("test_case_processing_chunk", chunk=index, total=len(chunks))
            chunk_output = self._run_single_generation(
                input_data=input_data,
                clean_description=clean_description,
                clean_acceptance_criteria=chunk,
                past_context=past_context if index == 1 else "",
                batch_index=index,
                batch_total=len(chunks),
            )
            logger.info(
                "test_case_chunk_complete",
                chunk=index,
                total=len(chunks),
                scenarios=chunk_output.total_scenarios,
            )
            merged_scenarios.extend(chunk_output.scenarios)
            if chunk_output.coverage_summary:
                coverage_parts.append(f"Batch {index}: {chunk_output.coverage_summary}")
            if chunk_output.model_used not in models:
                models.append(chunk_output.model_used)
            tokens_used += chunk_output.tokens_used

        for index, scenario in enumerate(merged_scenarios, 1):
            scenario.scenario_id = f"TC-{index:03d}"

        logger.info("test_case_chunked_complete", total=len(merged_scenarios))
        return TestCaseAgentOutput(
            feature=input_data.feature,
            scenarios=merged_scenarios,
            coverage_summary="\n".join(coverage_parts),
            total_scenarios=len(merged_scenarios),
            prompt_version=PROMPT_VERSION,
            model_used=", ".join(models) if models else "unknown",
            generated_at=datetime.now(),
            tokens_used=tokens_used,
        )

    def _parse_output(
        self,
        raw_json:   str,
        input_data: TestCaseAgentInput,
        model_used: str,
        tokens_used: int = 0,
    ) -> TestCaseAgentOutput:
        """Parse LLM JSON response into typed TestCaseAgentOutput."""
        # Clean common LLM artifacts
        raw = raw_json.strip()
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        raw = re.sub(r"```$", "", raw).strip()
        raw = _extract_json_object(raw)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("test_case_parse_json_failed", raw_preview=raw[:500])
            # Try to salvage truncated JSON
            last_bracket = raw.rfind("}]")
            if last_bracket != -1:
                raw = raw[:last_bracket + 2] + "}"
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("test_case_parse_salvage_failed", raw_preview=raw[:500])
                    data = _salvage_scenarios_from_truncated_json(raw, input_data.feature)
            else:
                data = _salvage_scenarios_from_truncated_json(raw, input_data.feature)

        scenario_items = (
            data.get("scenarios")
            or data.get("test_cases")
            or data.get("cases")
            or data.get("testcases")
            or []
        )
        if not scenario_items:
            logger.warning(
                "test_case_parse_no_scenarios",
                keys=list(data.keys()),
                coverage_summary=str(data.get("coverage_summary", ""))[:300],
            )

        scenarios = []
        for i, s in enumerate(scenario_items, 1):
            def _list_field(name: str) -> list[str]:
                value = s.get(name, [])
                if isinstance(value, list):
                    return [str(item) for item in value if str(item).strip()]
                if isinstance(value, str) and value.strip():
                    return [value.strip()]
                return []

            raw_steps = s.get("steps", [])
            steps = []
            if isinstance(raw_steps, str):
                for idx, line in enumerate(raw_steps.strip().split("\n")):
                    line = line.strip()
                    if line:
                        steps.append(TestStep(step_number=idx+1, action=line, expected=""))
                raw_steps = []
            for idx, st in enumerate(raw_steps):
                if isinstance(st, dict):
                    steps.append(TestStep(
                        step_number=st.get("step_number", idx+1),
                        action=st.get("action",""),
                        expected=st.get("expected",""),
                    ))
                elif isinstance(st, str):
                    steps.append(TestStep(step_number=idx+1, action=st, expected=""))
            try:
                # Map P0/P1/P2 → high/medium/low
                priority_raw = s.get("priority", "medium").upper()
                priority_map = {"P0": "high", "P1": "medium", "P2": "low",
                               "HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
                priority_val = priority_map.get(priority_raw, "medium")

                # Map test_type
                tt = s.get("test_type", "functional").lower()
                valid_types = ["smoke", "functional", "regression", "e2e", "negative", "boundary"]
                if tt not in valid_types:
                    tt = "functional"
            except Exception as map_err:
                import structlog as _sl
                _sl.get_logger(__name__).warning("scenario_field_mapping_error", error=str(map_err), scenario=s)
                continue

            raw_platforms = s.get("platforms") or s.get("platform") or [
                p.value for p in input_data.platforms
            ]
            if isinstance(raw_platforms, str):
                raw_platforms = [raw_platforms]

            normalized_platforms = []
            for raw_platform in raw_platforms:
                value = str(raw_platform).strip().lower()
                platform_map = {
                    "mobile": input_data.platforms[0].value if input_data.platforms else "android",
                    "flutter_android": "flutter-android",
                    "flutter-ios": "flutter-ios",
                    "flutter_ios": "flutter-ios",
                }
                value = platform_map.get(value, value)
                if value in Platform._value2member_map_:
                    normalized_platforms.append(Platform(value))
            if not normalized_platforms:
                normalized_platforms = input_data.platforms or [Platform.WEB]

            regression_candidate = s.get("regression_candidate", False)
            if isinstance(regression_candidate, str):
                regression_candidate = regression_candidate.strip().lower() in {"true", "yes", "1"}
            regression_candidate = bool(regression_candidate or tt == "regression")

            scenarios.append(ScenarioSchema(
                scenario_id=s.get("scenario_id", s.get("case_id", f"TC-{i:03d}")),
                name=s.get("name", s.get("title", f"Scenario {i}")),
                precondition=s.get("precondition", s.get("preconditions", "")),
                steps=steps,
                expected_result=s.get("expected_result", ""),
                test_data=s.get("test_data", {}),
                tags=s.get("tags", []),
                test_type=TestType(tt),
                platforms=normalized_platforms,
                priority=Priority({
                        "P0":"high","P1":"medium","P2":"low",
                        "high":"high","medium":"medium","low":"low"
                    }.get(s.get("priority","medium"),"medium")),
                edge_cases=_list_field("edge_cases"),
                combination_edge_cases=_list_field("combination_edge_cases"),
                weird_edge_cases=_list_field("weird_edge_cases"),
                regression_candidate=regression_candidate,
                regression_risk_area=_list_field("regression_risk_area"),
            ))

        return TestCaseAgentOutput(
            feature=input_data.feature,
            scenarios=scenarios,
            coverage_summary=data.get("coverage_summary", ""),
            total_scenarios=len(scenarios),
            prompt_version=PROMPT_VERSION,
            model_used=model_used,
            generated_at=datetime.now(),
            tokens_used=tokens_used,
        )

    async def _request_approval(self, output: TestCaseAgentOutput) -> TestCaseAgentOutput:
        """Send to Telegram, wait for QA Lead decision."""
        item = review_queue.enqueue(
            agent_name=AGENT_NAME,
            payload=output.model_dump(),
        )

        # Non-blocking send to Telegram
        await self.telegram.send_test_cases_for_review(
            output_id=item.output_id,
            feature=output.feature,
            scenarios=output.scenarios,
            model_used=output.model_used,
        )

        logger.info(
            "waiting_for_approval",
            output_id=item.output_id,
            feature=output.feature,
        )

        feedback: AgentFeedback = await item.wait(timeout=300.0)

        if feedback.decision == Decision.APPROVE:
            logger.info("test_cases_approved", output_id=item.output_id)
            return output

        elif feedback.decision == Decision.REJECT:
            logger.warning(
                "test_cases_rejected",
                output_id=item.output_id,
                reason=feedback.rejection_reason,
            )
            raise ValueError(
                f"Test cases rejected by reviewer. "
                f"Reason: {feedback.rejection_reason}. "
                f"Feedback: {feedback.corrected_output or 'None provided'}"
            )

        else:  # EDIT
            logger.info("test_cases_edit_requested", output_id=item.output_id)
            # For now return original — full edit flow is Phase 3
            return output


test_case_agent = TestCaseAgent()
