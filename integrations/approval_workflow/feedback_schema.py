"""
Approval Workflow — feedback schema + in-memory review queue.
Telegram bot calls approve/reject → result stored here → agent reads it.
"""
import uuid
import structlog
import asyncio
from datetime import datetime
from typing import Optional
from core.agent_contracts import AgentFeedback, Decision, RejectionReason

logger = structlog.get_logger(__name__)


class ReviewItem:
    def __init__(self, output_id: str, agent_name: str, payload: dict):
        self.output_id  = output_id
        self.agent_name = agent_name
        self.payload    = payload
        self.created_at = datetime.now()
        self.feedback:  Optional[AgentFeedback] = None
        self._event     = asyncio.Event()

    def resolve(self, feedback: AgentFeedback):
        self.feedback = feedback
        self._event.set()

    async def wait(self, timeout: float = 300.0) -> AgentFeedback:
        """Block until a reviewer approves/rejects. Timeout = 5 min."""
        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("review_timeout", output_id=self.output_id)
            # Auto-reject on timeout to prevent CI hanging
            self.feedback = AgentFeedback(
                output_id=self.output_id,
                decision=Decision.REJECT,
                rejection_reason=RejectionReason.INCOMPLETE_SCENARIO,
                corrected_output=None,
                reviewer_id="system_timeout",
            )
        return self.feedback


class ReviewQueue:
    def __init__(self):
        self._queue: dict[str, ReviewItem] = {}

    def enqueue(self, agent_name: str, payload: dict) -> ReviewItem:
        output_id = str(uuid.uuid4())[:8]
        item = ReviewItem(output_id, agent_name, payload)
        self._queue[output_id] = item
        logger.info("review_queued", output_id=output_id, agent=agent_name)
        return item

    def resolve(self, output_id: str, feedback: AgentFeedback):
        item = self._queue.get(output_id)
        if not item:
            logger.warning("review_not_found", output_id=output_id)
            return
        item.resolve(feedback)
        logger.info(
            "review_resolved",
            output_id=output_id,
            decision=feedback.decision.value,
        )

    def get(self, output_id: str) -> Optional[ReviewItem]:
        return self._queue.get(output_id)

    def pending(self) -> list[ReviewItem]:
        return [i for i in self._queue.values() if i.feedback is None]


review_queue = ReviewQueue()
