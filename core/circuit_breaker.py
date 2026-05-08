"""
Circuit Breaker — prevents cascading agent failures in CI/CD.
States: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing recovery)
"""
import structlog
from datetime import datetime, timedelta
from typing import Callable, Any

logger = structlog.get_logger(__name__)


class CircuitOpenError(Exception):
    def __init__(self, agent_name: str, last_failure: datetime):
        self.agent_name   = agent_name
        self.last_failure = last_failure
        super().__init__(
            f"Circuit OPEN for '{agent_name}'. "
            f"Last failure: {last_failure.isoformat()}. "
            f"Try again later or check agent health."
        )


class CircuitBreaker:
    def __init__(
        self,
        agent_name:        str,
        failure_threshold: int = 3,
        recovery_timeout:  int = 300,  # seconds
    ):
        self.agent_name        = agent_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout  = timedelta(seconds=recovery_timeout)
        self.failure_count     = 0
        self.last_failure:     datetime | None = None
        self.state             = "CLOSED"

    def call(self, fn: Callable, *args, **kwargs) -> Any:
        if self.state == "OPEN":
            if self._should_attempt_recovery():
                self.state = "HALF_OPEN"
                logger.info("circuit_half_open", agent=self.agent_name)
            else:
                raise CircuitOpenError(self.agent_name, self.last_failure)

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    def _should_attempt_recovery(self) -> bool:
        if self.last_failure is None:
            return True
        return datetime.now() - self.last_failure >= self.recovery_timeout

    def _on_success(self):
        if self.state == "HALF_OPEN":
            logger.info("circuit_recovered", agent=self.agent_name)
        self.failure_count = 0
        self.state         = "CLOSED"

    def _on_failure(self, error: Exception):
        self.failure_count += 1
        self.last_failure   = datetime.now()
        logger.warning(
            "circuit_failure",
            agent=self.agent_name,
            count=self.failure_count,
            threshold=self.failure_threshold,
            error=str(error),
        )
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(
                "circuit_opened",
                agent=self.agent_name,
                message=f"Circuit OPEN after {self.failure_count} failures.",
            )

    @property
    def is_open(self) -> bool:
        return self.state == "OPEN"


# Registry — one breaker per agent
_breakers: dict[str, CircuitBreaker] = {}

def get_breaker(agent_name: str) -> CircuitBreaker:
    if agent_name not in _breakers:
        _breakers[agent_name] = CircuitBreaker(agent_name)
    return _breakers[agent_name]
