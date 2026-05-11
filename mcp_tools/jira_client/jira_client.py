"""
MCP Jira Client — Full Jira integration for QA framework.
"""
import os
import base64
import httpx
import structlog
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")
logger = structlog.get_logger(__name__)


class JiraClient:
    def __init__(self):
        self.base_url = os.getenv("JIRA_BASE_URL", "")
        self.email    = os.getenv("JIRA_EMAIL", "")
        self.token    = os.getenv("JIRA_TOKEN", "")
        self.project  = os.getenv("JIRA_PROJECT_KEY", "HM")
        auth = base64.b64encode(f"{self.email}:{self.token}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json"
        }

    def _extract_adf_text(self, node) -> str:
        text = ""
        if isinstance(node, dict):
            if node.get("type") == "text":
                text += node.get("text", "")
            for child in node.get("content", []):
                text += self._extract_adf_text(child)
            if node.get("type") in ["paragraph", "listItem", "heading", "bulletList"]:
                text += "\n"
        return text

    def get_issue(self, issue_key: str) -> dict:
        with httpx.Client() as client:
            r = client.get(
                f"{self.base_url}/rest/api/3/issue/{issue_key}",
                headers=self.headers
            )
        r.raise_for_status()
        fields = r.json().get("fields", {})

        desc_raw  = fields.get("description", {})
        desc_text = self._extract_adf_text(desc_raw) if isinstance(desc_raw, dict) else str(desc_raw or "")

        ac_list = []
        for line in desc_text.split("\n"):
            line = line.strip().lstrip("-•").strip()
            if line and 15 < len(line) < 300:
                ac_list.append(line)

        subtasks = []
        for st in fields.get("subtasks", [])[:10]:
            st_key     = st.get("key")
            st_summary = st.get("fields", {}).get("summary", "")
            st_status  = st.get("fields", {}).get("status", {}).get("name", "")
            try:
                with httpx.Client() as client:
                    st_r = client.get(
                        f"{self.base_url}/rest/api/3/issue/{st_key}",
                        headers=self.headers
                    )
                st_desc_raw = st_r.json().get("fields", {}).get("description", {})
                st_desc = self._extract_adf_text(st_desc_raw) if isinstance(st_desc_raw, dict) else ""
            except Exception:
                st_desc = ""

            subtasks.append({
                "key": st_key,
                "summary": st_summary,
                "status": st_status,
                "description": st_desc[:300]
            })

        return {
            "key":                  issue_key,
            "summary":              fields.get("summary", ""),
            "status":               fields.get("status", {}).get("name", ""),
            "priority":             fields.get("priority", {}).get("name", ""),
            "issue_type":           fields.get("issuetype", {}).get("name", ""),
            "assignee":             (fields.get("assignee") or {}).get("displayName", "Unassigned"),
            "description":          desc_text.strip(),
            "acceptance_criteria":  ac_list,
            "subtasks":             subtasks,
            "labels":               fields.get("labels", []),
            "sprint":               next(
                (s.get("name") for s in (fields.get("customfield_10020") or [])
                 if s.get("state") == "active"), None
            )
        }

    def get_transitions(self, issue_key: str) -> list:
        with httpx.Client() as client:
            r = client.get(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions",
                headers=self.headers
            )
        return r.json().get("transitions", [])

    def transition_issue(self, issue_key: str, status_name: str) -> bool:
        transitions = self.get_transitions(issue_key)
        transition_id = next(
            (t["id"] for t in transitions if t["name"].upper() == status_name.upper()),
            None
        )
        if not transition_id:
            logger.warning("transition_not_found", issue=issue_key, status=status_name)
            return False
        with httpx.Client() as client:
            r = client.post(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions",
                headers=self.headers,
                json={"transition": {"id": transition_id}}
            )
        return r.status_code == 204

    def add_comment(self, issue_key: str, comment: str) -> bool:
        with httpx.Client() as client:
            r = client.post(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/comment",
                headers=self.headers,
                json={"body": {
                    "type": "doc", "version": 1,
                    "content": [{"type": "paragraph", "content": [
                        {"type": "text", "text": comment}
                    ]}]
                }}
            )
        return r.status_code == 201

    def search(self, jql: str, max_results: int = 10) -> list:
        with httpx.Client() as client:
            r = client.get(
                f"{self.base_url}/rest/api/3/search/jql",
                headers=self.headers,
                params={"jql": jql, "maxResults": max_results,
                        "fields": "summary,status,issuetype,assignee,priority"}
            )
        return [{
            "key":      i["key"],
            "summary":  i["fields"].get("summary", ""),
            "status":   i["fields"].get("status", {}).get("name", ""),
            "type":     i["fields"].get("issuetype", {}).get("name", ""),
            "assignee": (i["fields"].get("assignee") or {}).get("displayName", "Unassigned"),
        } for i in r.json().get("issues", [])]

    def post_test_results(self, issue_key: str, passed: int,
                          failed: int, skipped: int, run_url: str = "") -> bool:
        total = passed + failed + skipped
        icon  = "✅" if failed == 0 else "❌"
        rate  = f"{(passed/total*100):.0f}%" if total > 0 else "0%"
        comment = (
            f"{icon} QA Automation Results\n\n"
            f"Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}\n"
            f"Pass rate: {rate}"
        )
        if run_url:
            comment += f"\nRun: {run_url}"
        return self.add_comment(issue_key, comment)


jira_client = JiraClient()
