"""
CleanupRegistry — tracks test-created entities for teardown.

Opt-in for new tests. Existing tests continue working unchanged.

Usage in a test or fixture:
    from core.test_data.cleanup_registry import cleanup_registry

    # Register an entity created during the test
    cleanup_registry.register("user", user_id, lambda: delete_user(user_id))

    # In session/function teardown fixture:
    cleanup_registry.cleanup_all(run_id, worker_id)

Thread-safe: safe for pytest-xdist parallel runs when each worker uses
its own worker_id (use the `worker_id` fixture from xdist, or "main").
"""
from __future__ import annotations

import structlog
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Callable

logger = structlog.get_logger(__name__)


@dataclass
class _Entry:
    entity_type: str
    entity_id:   str
    cleanup_fn:  Callable[[], None]


class CleanupRegistry:
    """
    Thread-safe registry of test-created entities.

    Keyed by (run_id, worker_id) so parallel workers don't interfere.
    """

    def __init__(self) -> None:
        self._lock:    Lock = Lock()
        self._entries: dict[tuple[str, str], list[_Entry]] = defaultdict(list)

    def register(
        self,
        entity_type: str,
        entity_id:   str,
        cleanup_fn:  Callable[[], None],
        run_id:      str = "default",
        worker_id:   str = "main",
    ) -> None:
        """
        Register an entity for cleanup.

        entity_type: human label e.g. "user", "post", "report"
        entity_id:   unique identifier (UUID, email, slug)
        cleanup_fn:  zero-arg callable that deletes/reverts the entity
        run_id:      pipeline run ID or pytest session ID
        worker_id:   xdist worker ID ("main" for non-parallel runs)
        """
        with self._lock:
            self._entries[(run_id, worker_id)].append(
                _Entry(entity_type=entity_type, entity_id=entity_id, cleanup_fn=cleanup_fn)
            )
        logger.debug(
            "cleanup_registered",
            entity_type=entity_type,
            entity_id=entity_id,
            run_id=run_id,
            worker_id=worker_id,
        )

    def cleanup_all(self, run_id: str = "default", worker_id: str = "main") -> int:
        """
        Call every cleanup_fn registered under (run_id, worker_id) in LIFO order.
        Swallows individual errors so all cleanups are attempted.
        Returns the number of successful cleanups.
        """
        with self._lock:
            entries = list(self._entries.pop((run_id, worker_id), []))

        # LIFO — last created, first deleted
        entries.reverse()
        success = 0
        for entry in entries:
            try:
                entry.cleanup_fn()
                success += 1
                logger.debug(
                    "cleanup_done",
                    entity_type=entry.entity_type,
                    entity_id=entry.entity_id,
                )
            except Exception as e:
                logger.warning(
                    "cleanup_failed",
                    entity_type=entry.entity_type,
                    entity_id=entry.entity_id,
                    error=str(e),
                )

        if entries:
            logger.info(
                "cleanup_complete",
                run_id=run_id,
                worker_id=worker_id,
                total=len(entries),
                success=success,
                failed=len(entries) - success,
            )
        return success

    def pending_count(self, run_id: str = "default", worker_id: str = "main") -> int:
        """Return number of entities registered but not yet cleaned up."""
        with self._lock:
            return len(self._entries.get((run_id, worker_id), []))

    def clear(self, run_id: str = "default", worker_id: str = "main") -> None:
        """Remove entries without calling cleanup_fn. Use only for test skips."""
        with self._lock:
            self._entries.pop((run_id, worker_id), None)


# Module-level singleton — import this in tests and fixtures
cleanup_registry = CleanupRegistry()
