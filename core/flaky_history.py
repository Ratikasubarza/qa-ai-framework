"""
Flaky test history store — persists per-test outcome history across pipeline runs.

Each entry tracks outcomes (PASS/FAIL) and errors for one test, so the
FlakyTestAgent can compute alternation rates across multiple runs.

Storage: reports/metrics/test_history.json  (auto-created, append-only per run)
Format:
  {
    "test_name": {
      "outcomes": ["PASS", "FAIL", "PASS"],   # oldest → newest, capped at 20
      "errors":   ["", "AssertionError: ...", ""]
    }
  }
"""
from __future__ import annotations

import json
import structlog
from pathlib import Path
from threading import Lock

logger = structlog.get_logger(__name__)

_HISTORY_PATH = Path("reports/metrics/test_history.json")
_MAX_HISTORY  = 20   # outcomes kept per test
_lock         = Lock()


def _load() -> dict:
    if not _HISTORY_PATH.exists():
        return {}
    try:
        return json.loads(_HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("flaky_history_load_failed", error=str(e))
        return {}


def _save(data: dict) -> None:
    _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _HISTORY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def record_run(execution_results: dict[str, dict]) -> None:
    """
    Append current run outcomes to the persistent history.

    execution_results format (as written by node_execute):
      { fpath: { "passed": bool, "stdout": str, "stderr": str } }
    """
    with _lock:
        history = _load()
        for fpath, result in execution_results.items():
            test_name = Path(fpath).stem
            outcome   = "PASS" if result.get("passed") else "FAIL"
            error_msg = ""
            if outcome == "FAIL":
                raw = (result.get("stdout", "") + "\n" + result.get("stderr", ""))[-500:]
                error_msg = raw.strip()

            entry = history.setdefault(test_name, {"outcomes": [], "errors": []})
            entry["outcomes"].append(outcome)
            entry["errors"].append(error_msg)

            # Cap to avoid unbounded growth
            entry["outcomes"] = entry["outcomes"][-_MAX_HISTORY:]
            entry["errors"]   = entry["errors"][-_MAX_HISTORY:]

        _save(history)
        logger.info("flaky_history_recorded", tests=len(execution_results))


def get_history() -> list[dict]:
    """Return history in the format expected by FlakyTestAgent.analyze_batch."""
    with _lock:
        raw = _load()
    return [
        {
            "test_name": name,
            "outcomes":  entry.get("outcomes", []),
            "errors":    entry.get("errors", []),
        }
        for name, entry in raw.items()
    ]
