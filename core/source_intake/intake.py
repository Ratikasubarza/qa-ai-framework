"""Normalize Jira, Confluence, manual story, and URL inputs for the pipeline."""

from __future__ import annotations

from typing import Any

from core.agent_state import AgentState
from core.source_intake.security import redact_internal_text
from core.source_intake.subtask_filter import filter_subtasks_for_platforms


def is_placeholder_url(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in {"", "...", "…", "n/a", "na", "none", "null", "-"}


def format_jira_issue_context(
    issue: dict,
    include_subtasks: bool = False,
    platforms: list[str] | None = None,
) -> str:
    lines = [
        f"Jira Issue: {issue.get('key', '')}",
        f"Summary: {issue.get('summary', '')}",
        f"Status: {issue.get('status', '')}",
        f"Priority: {issue.get('priority', '')}",
        f"Issue Type: {issue.get('issue_type', '')}",
        "",
        "Description:",
        issue.get("description", ""),
    ]

    acceptance_criteria = issue.get("acceptance_criteria") or []
    if acceptance_criteria:
        lines.extend(["", "Acceptance Criteria:"])
        lines.extend(f"- {item}" for item in acceptance_criteria)

    if include_subtasks and issue.get("subtasks"):
        target_platforms = platforms or []
        subtasks = filter_subtasks_for_platforms(issue["subtasks"], target_platforms)
        platform_note = f" for {', '.join(target_platforms)}" if target_platforms else ""
        lines.extend(["", f"Developer Subtasks / Implementation Details{platform_note}:"])
        for subtask in subtasks:
            lines.extend([
                f"- {subtask.get('key', '')}: {subtask.get('summary', '')}",
                f"  Status: {subtask.get('status', '')}",
            ])
            if subtask.get("description"):
                lines.append(f"  Details: {subtask['description']}")

    return "\n".join(str(line) for line in lines if line is not None).strip()


def _source_refs(
    ticket_id: str,
    should_fetch_prd: bool,
    prd_url: str,
    story_text: str,
    feature_url: str,
) -> list[dict[str, str]]:
    refs = []
    if ticket_id:
        refs.append({"type": "jira", "ref": ticket_id})
    if should_fetch_prd:
        refs.append({"type": "confluence", "ref": prd_url})
    if story_text:
        refs.append({"type": "manual_story", "ref": "story_text"})
    if feature_url:
        refs.append({"type": "feature_url", "ref": feature_url})
    return refs


def build_source_intake_state(state: AgentState, logger: Any) -> AgentState:
    story_text = state.get("story_text") or state.get("feature", "")
    ticket_id = state.get("ticket_id") or ""
    platforms = state.get("platforms") or ["web"]
    feature_url = state.get("feature_url") or ""
    prd_url = state.get("prd_url") or ""
    include_subtasks = bool(state.get("include_subtasks"))
    prd_source: dict[str, Any] = {}
    jira_source: dict[str, Any] = {}
    intake_error: dict[str, Any] | None = None
    context_parts: list[str] = []
    should_fetch_prd = bool(prd_url) and not is_placeholder_url(prd_url)

    source_refs = _source_refs(
        ticket_id=ticket_id,
        should_fetch_prd=should_fetch_prd,
        prd_url=prd_url,
        story_text=story_text,
        feature_url=feature_url,
    )

    if ticket_id:
        try:
            from mcp_tools.jira_client.jira_client import jira_client

            issue = jira_client.get_issue(ticket_id)
            jira_text = format_jira_issue_context(
                issue,
                include_subtasks=include_subtasks,
                platforms=platforms,
            )
            if jira_text:
                context_parts.append(f"=== JIRA STORY / TICKET ===\n{jira_text}")
            raw_subtasks = issue.get("subtasks") or []
            included_subtasks = (
                filter_subtasks_for_platforms(raw_subtasks, platforms)
                if include_subtasks
                else []
            )
            jira_source = {
                "type": "jira",
                "key": issue.get("key", ticket_id),
                "summary": issue.get("summary", ""),
                "status": issue.get("status", ""),
                "priority": issue.get("priority", ""),
                "subtasks_included": include_subtasks,
                "subtask_count": len(raw_subtasks),
                "included_subtask_count": len(included_subtasks),
                "subtask_filter_platforms": platforms if include_subtasks else [],
                "fetched": True,
            }
            logger.info(
                "jira_issue_fetched_for_intake",
                key=ticket_id,
                subtasks=jira_source["subtask_count"],
                included_subtasks=jira_source["included_subtask_count"],
                include_subtasks=include_subtasks,
            )
        except Exception as e:
            logger.warning("jira_intake_fetch_failed", ticket=ticket_id, error=str(e))
            jira_source = {
                "type": "jira",
                "key": ticket_id,
                "fetched": False,
                "error": str(e),
            }

    if prd_url and not should_fetch_prd:
        logger.warning("prd_url_placeholder_ignored", prd_url=prd_url)

    if should_fetch_prd:
        try:
            from mcp_tools.confluence_client.confluence_client import confluence_client

            page = confluence_client.fetch_page(prd_url)
            prd_text = (
                f"Source: {page['source_url']}\n"
                f"Title: {page['title']}\n"
                f"Space: {page['space_key']}\n\n"
                f"{page['body_text']}"
            ).strip()
            context_parts.append(f"=== PRODUCT PRD CONTEXT ===\n{prd_text}")
            prd_source = {
                "type": "confluence",
                "url": prd_url,
                "page_id": page["id"],
                "title": page["title"],
                "space_key": page["space_key"],
                "version": page.get("version"),
                "fetched": True,
            }
        except Exception as e:
            logger.error("confluence_fetch_failed", prd_url=prd_url, error=str(e))
            has_manual_fallback = bool(story_text.strip()) and story_text.strip() != state.get("feature", "")
            prd_source = {
                "type": "confluence",
                "url": prd_url,
                "fetched": False,
                "error": str(e),
            }
            if not has_manual_fallback:
                intake_error = {
                    "phase": "source_intake",
                    "message": f"Could not fetch Confluence PRD: {e}",
                }

    manual_story_is_real = bool(story_text.strip()) and story_text.strip() != state.get("feature", "")
    if manual_story_is_real:
        context_parts.append(f"=== MANUAL STORY CONTEXT ===\n{story_text.strip()}")

    if context_parts:
        story_text = "\n\n".join(context_parts)

    redaction = redact_internal_text(story_text)
    story_text = redaction.text

    source_bundle = {
        "feature": state.get("feature", ""),
        "platforms": platforms,
        "ticket_id": ticket_id,
        "prd_url": prd_url,
        "prd_content": story_text,
        "prd_source": prd_source,
        "jira_source": jira_source,
        "include_subtasks": include_subtasks,
        "feature_url": feature_url,
        "existing_test_cases": state.get("existing_test_cases") or [],
        "source_refs": source_refs,
        "security": {
            "classification": "internal" if source_refs else "unclassified",
            "redactions_applied": redaction.redactions,
            "safe_for_llm": True,
        },
        "intake_quality": {
            "has_ticket": bool(ticket_id),
            "jira_fetched": bool(jira_source.get("fetched")),
            "subtasks_included": include_subtasks,
            "has_prd_content": bool(story_text.strip()),
            "has_prd_url": should_fetch_prd,
            "prd_fetched": bool(prd_source.get("fetched")),
            "has_feature_url": bool(feature_url),
        },
    }

    return {
        **state,
        "current_phase": "source_intake",
        "source_bundle": source_bundle,
        "story_text": story_text,
        "error": intake_error,
    }
