"""
Pending Approvals Store — file-backed state for async human approval.

Saves pipeline state to reports/pending_approvals/{approval_id}.json so it
survives server restarts. The QA Lead approves via Telegram or cli.py; the
resolve() method marks the record and optionally triggers GitHub Actions
workflow_dispatch to resume the pipeline.
"""
import json
import structlog
from datetime import datetime, timedelta
from pathlib import Path

logger = structlog.get_logger(__name__)

STORE_DIR = Path("reports/pending_approvals")


class PendingApprovalStore:
    def __init__(self, store_dir: Path = STORE_DIR):
        self._dir = Path(store_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, approval_id: str) -> Path:
        return self._dir / f"{approval_id}.json"

    def save(self, approval_id: str, state: dict, expires_hours: int = 24) -> None:
        """Persist pipeline state while waiting for human approval."""
        now = datetime.utcnow()
        payload = {
            "approval_id":  approval_id,
            "state":        state,
            "created_at":   now.isoformat(),
            "expires_at":   (now + timedelta(hours=expires_hours)).isoformat(),
            "ticket_id":    state.get("ticket_id", ""),
            "feature":      state.get("feature", ""),
            "confidence":   state.get("confidence_score", 0.0),
            "status":       "pending",
            "decision":     None,
            "reason":       "",
        }
        self._path(approval_id).write_text(
            json.dumps(payload, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info(
            "pending_approval_saved",
            approval_id=approval_id,
            feature=state.get("feature", ""),
            expires_hours=expires_hours,
        )

    def load(self, approval_id: str) -> dict | None:
        """Load state; returns None if not found or expired."""
        path = self._path(approval_id)
        if not path.exists():
            logger.warning("pending_approval_not_found", approval_id=approval_id)
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("pending_approval_load_error", approval_id=approval_id, error=str(e))
            return None

        expires_at = datetime.fromisoformat(payload["expires_at"])
        if datetime.utcnow() > expires_at:
            logger.warning("pending_approval_expired", approval_id=approval_id)
            return None

        return payload

    def resolve(self, approval_id: str, decision: str, reason: str = "") -> bool:
        """
        Mark as resolved and attempt to trigger pipeline resume via GitHub Actions.
        Returns False if the record is not found or expired.
        """
        payload = self.load(approval_id)
        if payload is None:
            return False

        payload["status"]      = "resolved"
        payload["decision"]    = decision
        payload["reason"]      = reason
        payload["resolved_at"] = datetime.utcnow().isoformat()

        self._path(approval_id).write_text(
            json.dumps(payload, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info(
            "pending_approval_resolved",
            approval_id=approval_id,
            decision=decision,
        )

        # Best-effort: trigger pipeline resume via canonical workflow_dispatch contract
        try:
            from integrations.github_client import github_client as gh
            state = payload.get("state", {}) or {}
            environment = str(state.get("environment", "staging")).strip().lower() or "staging"
            test_suite = str(state.get("test_suite", "all")).strip().lower() or "all"
            ok = gh.trigger_workflow(
                workflow_id="qa-pipeline.yml",
                inputs={
                    "environment": environment,
                    "test_suite": test_suite,
                    "test_level": "approval_resume",
                },
            )
            logger.info(
                "pipeline_resume_triggered",
                approval_id=approval_id,
                workflow="qa-pipeline.yml",
                ok=ok,
                environment=environment,
                test_suite=test_suite,
                decision=decision,
            )
        except Exception as e:
            logger.warning(
                "pipeline_resume_skipped",
                approval_id=approval_id,
                error=str(e),
            )

        return True

    def list_pending(self) -> list[dict]:
        """Return all pending (non-expired, non-resolved) approvals."""
        results = []
        for path in sorted(self._dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if payload.get("status") != "pending":
                    continue
                expires_at = datetime.fromisoformat(payload["expires_at"])
                if datetime.utcnow() > expires_at:
                    continue
                results.append(payload)
            except Exception:
                continue
        return results

    def cleanup_expired(self) -> int:
        """Delete expired records. Returns count of deleted files."""
        count = 0
        for path in sorted(self._dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                expires_at = datetime.fromisoformat(payload["expires_at"])
                if datetime.utcnow() > expires_at:
                    path.unlink()
                    count += 1
            except Exception:
                continue
        if count:
            logger.info("pending_approvals_cleaned", count=count)
        return count
