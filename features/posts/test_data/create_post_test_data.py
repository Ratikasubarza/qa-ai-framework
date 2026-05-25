"""
Create Post Test Data — POST /v1/posts

Two interfaces:
  1. CreatePostTestData  (class constants) — static reference values
  2. CreatePostPayload   (dataclass)       — Builder pattern for parameterized tests
"""
import os
import time
from dataclasses import dataclass, field
from core.test_data.base_builder import PayloadBuilder
from config.test_config import ReferenceIDs

# ── Topic IDs — sourced from ReferenceIDs (single source of truth) ────────────
TOPIC_PODCASTING            = ReferenceIDs.TOPIC_PODCASTING
TOPIC_CAREER                = ReferenceIDs.TOPIC_CAREER
TOPIC_LEADERSHIP            = ReferenceIDs.TOPIC_LEADERSHIP
TOPIC_SOCIAL                = ReferenceIDs.TOPIC_SOCIAL
TOPIC_COMMUNITY_ENGAGEMENT  = ReferenceIDs.TOPIC_COMMUNITY_ENGAGEMENT

# Sample S3 media URL — override via SAMPLE_MEDIA_URL env var in CI
SAMPLE_MEDIA_URL = os.getenv(
    "SAMPLE_MEDIA_URL",
    "https://hono-assets-dev.s3.ap-southeast-1.amazonaws.com"
    "/media/2026/04/23/1872db3a-cd67-4124-9d72-bbbc1de72c67.jpg",
)


# ── Builder ───────────────────────────────────────────────────────────────────

@dataclass
class CreatePostPayload(PayloadBuilder):
    content:      str  = field(default_factory=lambda: f"QA test post {int(time.time())} — automated")
    visibility:   str  = "PUBLIC"
    is_anonymous: bool = False
    topic_ids:    list = field(default_factory=lambda: [TOPIC_PODCASTING])
    media:        list = field(default_factory=list)
    mentions:     list = field(default_factory=list)

    def as_dict(self) -> dict:
        d: dict = {
            "content":      self.content,
            "visibility":   self.visibility,
            "is_anonymous": self.is_anonymous,
            "topic_ids":    self.topic_ids,
        }
        if self.media:
            d["media"] = self.media
        if self.mentions:
            d["mentions"] = self.mentions
        return d

    # ── Named constructors ────────────────────────────────────────────────────

    @classmethod
    def valid(cls) -> "CreatePostPayload":
        return cls()

    @classmethod
    def with_media(cls) -> "CreatePostPayload":
        return cls(media=[SAMPLE_MEDIA_URL])

    @classmethod
    def anonymous(cls) -> "CreatePostPayload":
        return cls(is_anonymous=True)

    @classmethod
    def multiple_topics(cls) -> "CreatePostPayload":
        return cls(topic_ids=[TOPIC_PODCASTING, TOPIC_CAREER, TOPIC_LEADERSHIP])

    @classmethod
    def no_topics(cls) -> "CreatePostPayload":
        return cls(topic_ids=[])

    @classmethod
    def empty_content(cls) -> "CreatePostPayload":
        return cls(content="")

    @classmethod
    def long_content(cls, length: int = 5000) -> "CreatePostPayload":
        return cls(content="A" * length)

    @classmethod
    def with_visibility(cls, visibility: str) -> "CreatePostPayload":
        return cls(visibility=visibility)


# ── Static reference values ───────────────────────────────────────────────────

class CreatePostTestData:
    # Expected response codes
    SUCCESS_CODE        = "OK"
    SUCCESS_MESSAGE     = "Data saved"
    VALIDATION_CODE     = "NOKUNPROC"

    # Expected error messages
    ERROR_NO_TOPICS     = "at least 1 topic is required"
    ERROR_MENTION_BLOCKED = "user does not allow mentions from you"

    # Visibility values
    VISIBILITY_PUBLIC   = "PUBLIC"
    VISIBILITY_EVERYONE = "EVERYONE"
    VISIBILITY_INVALID  = "INVALID_VISIBILITY"

    # Response schema — required keys in data
    REQUIRED_RESPONSE_KEYS = {
        "id", "content", "visibility", "is_anonymous",
        "topics", "engagement", "created_at",
    }

    REQUIRED_ENGAGEMENT_KEYS = {
        "like_count", "comment_count", "repost_count", "view_count"
    }

    # Performance SLA
    MAX_RESPONSE_MS     = 5000
