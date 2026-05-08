"""
Locator Store — ChromaDB-backed storage for locator history.
Stores successful locators so self-healer can find similar ones
when a locator breaks.
"""
import json
import structlog
from datetime import datetime
from pathlib import Path
from knowledge_base.rag_engine import rag_engine

logger = structlog.get_logger(__name__)

COLLECTION = "locator_history"


class LocatorStore:
    def save(
        self,
        feature:  str,
        element:  str,
        locator:  str,
        platform: str = "web",
        success:  bool = True,
    ):
        """Save a locator to history — successful or failed."""
        doc_id  = f"{feature}_{element}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        content = (
            f"Feature: {feature}\n"
            f"Element: {element}\n"
            f"Locator: {locator}\n"
            f"Platform: {platform}\n"
            f"Success: {success}"
        )
        rag_engine.index(
            documents=[content],
            ids=[doc_id],
            metadatas=[{
                "feature":  feature,
                "element":  element,
                "locator":  locator,
                "platform": platform,
                "success":  str(success),
                "saved_at": datetime.now().isoformat(),
                "source":   "locator_history",
            }],
            collection=COLLECTION,
        )
        logger.info("locator_saved", feature=feature, element=element, success=success)

    def get_history(self, feature: str, element: str, top_k: int = 5) -> list[dict]:
        """Get past locators for a given feature+element combination."""
        query   = f"Feature: {feature} Element: {element}"
        results = rag_engine.retrieve(
            query=query,
            collection=COLLECTION,
            top_k=top_k,
            where={"feature": feature},
        )
        return results

    def snapshot(self, feature: str, locators: dict[str, str]):
        """
        Snapshot current locators before a test run.
        locators = {"email_field": "input[type='email']", ...}
        """
        for element, locator in locators.items():
            self.save(feature=feature, element=element, locator=locator, success=True)
        logger.info("locator_snapshot_saved", feature=feature, count=len(locators))


locator_store = LocatorStore()
