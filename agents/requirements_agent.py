"""
Requirements Agent v2.0 — chunked AC extraction, no AC limit.
"""
import json
import structlog
from core.llm_client import llm_client, ModelTier
from core.agent_contracts import (
    AcceptanceCriteriaOutput, AcceptanceCriteria,
    QATicketDraft, AmbiguityFlag, AssumptionNote,
    TestType, Platform, Priority,
)
from core.circuit_breaker import get_breaker
from core import input_sanitizer
from core.prompt_manager import prompt_manager
from knowledge_base.rag_engine import rag_engine
from skills.reporting.jira_connector import jira_connector

logger = structlog.get_logger(__name__)

AGENT_NAME     = "requirements_agent"
AC_PROMPT      = "ac_extraction"
PROMPT_VERSION = "1.0.0"


class RequirementsAgent:
    def __init__(self):
        self.breaker = get_breaker(AGENT_NAME)

    def run_from_jira(self, story_key: str) -> dict:
        logger.info("requirements_agent_start", story_key=story_key)
        story_text   = jira_connector.get_story_text(story_key, include_attachments=False)
        issue        = jira_connector.get_issue(story_key)
        fields       = issue.get("fields", {})
        summary      = fields.get("summary", story_key)
        priority     = fields.get("priority", {}).get("name", "Medium")
        logger.info("story_fetched", key=story_key, summary=summary[:60])

        clean        = input_sanitizer.sanitize(story_text, source=f"jira/{story_key}")
        past_context = rag_engine.retrieve(query=clean.content[:300], top_k=5)
        ac_output    = self._extract_ac(clean.content, story_key, past_context)
        logger.info("ac_extracted", criteria_count=len(ac_output.criteria), ambiguities=len(ac_output.ambiguities))

        drafts = self._generate_tickets(ac_output, story_key, summary, priority)
        logger.info("tickets_generated", count=len(drafts))
        logger.info("dry_run_mode", drafts=len(drafts))

        return {
            "story_key":       story_key,
            "story_summary":   summary,
            "feature":         ac_output.feature,
            "source_ref":      ac_output.source_ref,
            "ac_count":        len(ac_output.criteria),
            "criteria":        [c.model_dump(mode="json") for c in ac_output.criteria],
            "acceptance_criteria": [c.summary for c in ac_output.criteria],
            "ambiguities":     [a.model_dump() for a in ac_output.ambiguities],
            "assumptions":     [a.model_dump() for a in ac_output.assumptions],
            "ticket_drafts":   [d.model_dump() for d in drafts],
            "tickets_created": [],
            "tickets_failed":  [],
            "out_of_scope":    ac_output.out_of_scope,
            "missing_data":    ac_output.missing_data,
        }

    def run_from_confluence(
        self,
        prd_url: str,
        jira_story_keys: list[str] | None = None,
        feature: str = "",
    ) -> dict:
        """
        Extract ACs from a Confluence PRD (text + images) and cross-reference
        with one or more Jira tickets + their subtasks.

        Returns the same shape as run_from_jira() with extra keys:
          prd_source, prd_title, jira_contexts, image_descriptions
        """
        from mcp_tools.confluence_client.confluence_client import ConfluenceClient
        from mcp_tools.jira_client.jira_client import jira_client as _jira

        confluence = ConfluenceClient()

        # ── 1. Fetch PRD text ────────────────────────────────────────────────
        page = confluence.fetch_page(prd_url)
        page_id   = page["id"]
        prd_title = page.get("title", prd_url)
        prd_text  = page.get("body_text", "")
        source_ref = feature or prd_title

        logger.info("prd_fetched", page_id=page_id, title=prd_title, chars=len(prd_text))

        # ── 2. Fetch + describe images in PRD ───────────────────────────────
        image_descriptions = confluence.describe_images_with_llm(page_id)
        if image_descriptions:
            prd_text = prd_text + "\n\n--- VISUAL CONTENT ---\n" + image_descriptions
            logger.info("prd_images_merged", page_id=page_id)

        # ── 3. Fetch Jira context (multi-ticket + subtasks) ─────────────────
        jira_context_blocks: list[str] = []
        jira_ac_lines:       list[str] = []

        for key in (jira_story_keys or []):
            try:
                issue = _jira.get_issue(key)
                lines = [
                    f"JIRA {issue['key']} — {issue.get('summary', '')}",
                    f"Status: {issue.get('status', '')}  Priority: {issue.get('priority', '')}",
                ]
                if issue.get("description"):
                    lines.append(f"Description:\n{issue['description'][:800]}")

                # Subtasks — full context
                for st in issue.get("subtasks", []):
                    lines.append(
                        f"  Subtask [{st['key']}] {st['summary']} ({st['status']})"
                        + (f"\n    {st['description'][:200]}" if st.get("description") else "")
                    )

                # Collect ACs from Jira for cross-reference
                jira_ac_lines.extend(issue.get("acceptance_criteria", []))
                jira_context_blocks.append("\n".join(lines))
                logger.info("jira_ticket_fetched", key=key)
            except Exception as e:
                logger.warning("jira_fetch_failed", key=key, error=str(e))

        # ── 4. Build unified content for AC extraction ───────────────────────
        parts = [f"PRD: {prd_title}\n\n{prd_text}"]
        if jira_context_blocks:
            parts.append("JIRA HISTORY:\n" + "\n\n".join(jira_context_blocks))
        if jira_ac_lines:
            parts.append("EXISTING AC FROM JIRA (cross-reference — avoid duplicating, flag gaps):\n"
                         + "\n".join(f"- {a}" for a in jira_ac_lines))

        unified_content = "\n\n---\n".join(parts)
        clean = input_sanitizer.sanitize(unified_content, source=f"confluence/{page_id}")

        # ── 5. Extract ACs via LLM ───────────────────────────────────────────
        past_context = rag_engine.retrieve(query=clean.content[:300], top_k=5)
        ac_output    = self._extract_ac(clean.content, source_ref, past_context)
        logger.info("ac_extracted_from_prd", criteria_count=len(ac_output.criteria))

        drafts = self._generate_tickets(
            ac_output,
            story_key=",".join(jira_story_keys or []) or source_ref,
            story_summary=prd_title,
            story_priority="Medium",
        )

        return {
            "feature":         ac_output.feature or source_ref,
            "source_ref":      ac_output.source_ref,
            "prd_source":      prd_url,
            "prd_title":       prd_title,
            "jira_contexts":   jira_story_keys or [],
            "image_descriptions": bool(image_descriptions),
            "ac_count":        len(ac_output.criteria),
            "criteria":        [c.model_dump(mode="json") for c in ac_output.criteria],
            "acceptance_criteria": [c.summary for c in ac_output.criteria],
            "ambiguities":     [a.model_dump() for a in ac_output.ambiguities],
            "assumptions":     [a.model_dump() for a in ac_output.assumptions],
            "ticket_drafts":   [d.model_dump() for d in drafts],
            "out_of_scope":    ac_output.out_of_scope,
            "missing_data":    ac_output.missing_data,
        }

    def run_from_text(self, feature: str, story_text: str, parent_key: str = "") -> dict:
        clean        = input_sanitizer.sanitize(story_text, source="manual_input")
        past_context = rag_engine.retrieve(query=clean.content[:300], top_k=5)
        ac_output    = self._extract_ac(clean.content, feature, past_context)
        drafts       = self._generate_tickets(ac_output, parent_key or feature, feature, "Medium")
        return {
            "feature":       feature,
            "source_ref":    ac_output.source_ref,
            "ac_count":      len(ac_output.criteria),
            "criteria":      [c.model_dump(mode="json") for c in ac_output.criteria],
            "acceptance_criteria": [c.summary for c in ac_output.criteria],
            "ambiguities":   [a.model_dump() for a in ac_output.ambiguities],
            "assumptions":   [a.model_dump() for a in ac_output.assumptions],
            "ticket_drafts": [d.model_dump() for d in drafts],
            "out_of_scope":  ac_output.out_of_scope,
            "missing_data":  ac_output.missing_data,
        }

    def _extract_ac(self, content: str, source_ref: str, past_context: str) -> AcceptanceCriteriaOutput:
        if len(content) > 2000:
            return self._extract_ac_chunked(content, source_ref, past_context)
        return self._extract_ac_single(content, source_ref, past_context)

    def _extract_ac_chunked(self, content: str, source_ref: str, past_context: str) -> AcceptanceCriteriaOutput:
        chunk_size = 1500
        overlap    = 200
        chunks     = []
        start      = 0
        while start < len(content):
            end = min(start + chunk_size, len(content))
            chunks.append(content[start:end])
            start += chunk_size - overlap

        logger.info("ac_chunked_extraction", chunks=len(chunks))

        all_criteria    = []
        all_ambiguities = []
        all_assumptions = []
        out_of_scope    = []
        missing_data    = []
        feature         = source_ref

        for i, chunk in enumerate(chunks):
            logger.info("processing_chunk", chunk=i + 1, total=len(chunks))
            try:
                result   = self._extract_ac_single(
                    content=chunk,
                    source_ref=f"{source_ref}_chunk{i+1}",
                    past_context=past_context if i == 0 else "",
                )
                existing = {c.summary.lower() for c in all_criteria}
                for c in result.criteria:
                    if c.summary.lower() not in existing:
                        c.ac_id = f"AC-{len(all_criteria)+1:03d}"
                        all_criteria.append(c)
                        existing.add(c.summary.lower())
                all_ambiguities.extend(result.ambiguities)
                all_assumptions.extend(result.assumptions)
                out_of_scope.extend(result.out_of_scope)
                missing_data.extend(result.missing_data)
                if result.feature and result.feature != source_ref:
                    feature = result.feature
            except Exception as e:
                logger.warning("chunk_failed", chunk=i+1, error=str(e))

        logger.info("ac_chunked_complete", total=len(all_criteria))
        return AcceptanceCriteriaOutput(
            source_ref=source_ref,
            feature=feature,
            criteria=all_criteria,
            ambiguities=all_ambiguities,
            assumptions=all_assumptions,
            out_of_scope=list(set(out_of_scope)),
            missing_data=list(set(missing_data)),
            prompt_version=PROMPT_VERSION,
        )

    def _extract_ac_single(self, content: str, source_ref: str, past_context: str) -> AcceptanceCriteriaOutput:
        template = prompt_manager.get(AC_PROMPT)
        system   = template.format(content=content, source_ref=source_ref, past_context=past_context)

        def _call():
            return llm_client.complete_text(
                system=system,
                user=f"Extract acceptance criteria from: {source_ref}",
                tier=ModelTier.STANDARD,
                agent_name=AGENT_NAME,
                json_mode=True,
            )

        response = self.breaker.call(_call)
        logger.debug("ac_raw_response", content=str(response.content)[:200])
        return self._parse_ac_output(response.content, source_ref)

    def _parse_ac_output(self, raw, source_ref: str) -> AcceptanceCriteriaOutput:
        empty = AcceptanceCriteriaOutput(source_ref=source_ref, feature=source_ref, criteria=[], ambiguities=[])
        if not raw:
            return empty

        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("ac_parse_truncated", error=str(e))
            try:
                last = raw.rfind('"}')
                if last != -1:
                    data = json.loads(raw[:last+2] + ']}')
                else:
                    return empty
            except Exception:
                logger.error("ac_parse_failed")
                return empty

        criteria = []
        for item in data.get("criteria", []):
            try:
                criteria.append(AcceptanceCriteria(
                    ac_id=item.get("ac_id", f"AC-{len(criteria)+1:03d}"),
                    summary=item.get("summary", ""),
                    given=item.get("given", ""),
                    when=item.get("when", []),
                    then=item.get("then", []),
                    edge_cases=item.get("edge_cases", []),
                    test_types=[TestType(t) for t in item.get("test_types", ["functional"])
                                if t in TestType._value2member_map_],
                    platforms=[Platform(p) for p in item.get("platforms", ["web"])
                               if p in Platform._value2member_map_],
                    priority=Priority(item.get("priority", "medium")),
                ))
            except Exception as e:
                logger.warning("ac_item_failed", error=str(e))

        return AcceptanceCriteriaOutput(
            source_ref=source_ref,
            feature=data.get("feature", source_ref),
            criteria=criteria,
            ambiguities=[
                AmbiguityFlag(**a) for a in data.get("ambiguities", [])
                if all(k in a for k in ["field","description","impact","suggested_question"])
            ],
            assumptions=[
                AssumptionNote(**a) for a in data.get("assumptions", [])
                if all(k in a for k in ["assumption","based_on","risk"])
            ],
            out_of_scope=data.get("out_of_scope", []),
            missing_data=data.get("missing_data", []),
            prompt_version=PROMPT_VERSION,
        )

    def _generate_tickets(self, ac_output, story_key, story_summary, story_priority) -> list[QATicketDraft]:
        drafts = []
        for ac in ac_output.criteria:
            for test_type in (ac.test_types or [TestType.FUNCTIONAL]):
                for platform in (ac.platforms or [Platform.WEB]):
                    title = f"[QA] {ac_output.feature} — {ac.summary} [{test_type.value.upper()}]"
                    drafts.append(QATicketDraft(
                        title=title[:200],
                        issue_type="Task",
                        priority=story_priority,
                        labels=[test_type.value, f"platform-{platform.value}", "ai-generated"],
                        parent_key=story_key,
                        linked_story=story_key,
                        test_type=test_type,
                        platform=platform,
                        precondition=ac.given,
                        steps=[f"{i+1}. {w}" for i, w in enumerate(ac.when)],
                        expected="\n".join(ac.then),
                        edge_cases=ac.edge_cases,
                        source_ac_id=ac.ac_id,
                        generated_by=f"{AGENT_NAME} v2.0",
                        prompt_version=PROMPT_VERSION,
                        automation_candidate=test_type in [
                            TestType.SMOKE,
                            TestType.FUNCTIONAL,
                            TestType.REGRESSION,
                        ],
                    ))
        return drafts


requirements_agent = RequirementsAgent()
