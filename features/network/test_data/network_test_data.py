"""
Network Test Data — followers / following / suggestions endpoints

Two interfaces:
  1. NetworkTestData     (class constants) — static reference values and pagination defaults
  2. FollowPayload       (dataclass)       — Builder for follow/unfollow request bodies
"""
from dataclasses import dataclass
from core.test_data.base_builder import PayloadBuilder


@dataclass
class FollowPayload(PayloadBuilder):
    """Body for POST /v1/network/follow or similar follow-action endpoints."""
    target_user_id: str = ""

    @classmethod
    def for_user(cls, user_id: str) -> "FollowPayload":
        return cls(target_user_id=user_id)

    @classmethod
    def missing_target(cls) -> dict:
        return cls().without("target_user_id")

    @classmethod
    def invalid_id(cls) -> "FollowPayload":
        return cls(target_user_id="not-a-uuid")


class NetworkTestData:
    # Pagination defaults
    DEFAULT_PAGE  = 1
    DEFAULT_LIMIT = 10

    # Query limits
    MIN_LIMIT = 1
    MAX_LIMIT = 100

    # Expected response values
    SUCCESS_CODE = "OK"

    # Required keys in each follower/following list item
    REQUIRED_USER_KEYS = {"id", "fullname"}

    # Suggestions item shape — either top-level id or nested creator
    SUGGESTIONS_ID_KEYS = {"id", "creator"}

    # Performance SLA
    MAX_RESPONSE_MS = 3000

    # Pagination params
    @staticmethod
    def page_params(page: int = 1, limit: int = 10) -> dict:
        return {"page": page, "limit": limit}

    @staticmethod
    def search_params(query: str, page: int = 1, limit: int = 10) -> dict:
        return {"page": page, "limit": limit, "query": query}
