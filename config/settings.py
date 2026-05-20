from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── AI Provider ───────────────────────────────────────
    openrouter_api_key: str = Field(..., description="OpenRouter API key")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # ── Jira ──────────────────────────────────────────────
    jira_base_url: str = Field(..., description="Jira base URL")
    jira_email: str = Field(..., description="Jira account email")
    jira_token: str = Field(..., description="Jira API token")
    jira_project_key: str = "QA"

    # ── Telegram ──────────────────────────────────────────
    telegram_bot_token: str = Field(..., description="Telegram Bot token")
    telegram_qa_leads_chat_id: str = Field(..., description="QA Leads group chat ID")
    telegram_qa_team_chat_id: str = Field(..., description="QA Team group chat ID")
    telegram_qa_ops_chat_id: str = Field(..., description="QA Ops group chat ID")
    telegram_qa_bugs_chat_id: str = Field(..., description="QA Bugs group chat ID")

    # ── App ───────────────────────────────────────────────
    env: str = "development"
    log_level: str = "INFO"
    approval_required: bool = True

    # ── Approval thresholds ───────────────────────────────
    # APPROVAL_MODE: "smart" (3-tier) | "always" (require human) | "never" (auto-approve all)
    approval_mode: str = Field(default="smart")
    auto_approve_threshold: float = Field(default=0.85)
    auto_reject_threshold: float = Field(default=0.60)
    approval_timeout_hours: int = Field(default=24)

    # ── App URLs ──────────────────────────────────────────
    hono_api_url:     str = Field(..., description="Hono API URL — required; set in .env")
    hono_web_url:     str = Field(..., description="Hono web app URL — required; set in .env")
    hono_cms_url:     str = Field(..., description="Hono CMS URL — required; set in .env")
    hono_api_key:     str = Field("", description="Hono API key from environment")
    staging_email:    str = Field("", description="Staging account email from environment")
    staging_password: str = Field("", description="Staging account password from environment")
    staging_cms_email: str = Field("", description="CMS account email from environment")
    staging_cms_password: str = Field("", description="CMS account password from environment")
    chroma_persist_dir: str = "./knowledge_base/vector_store"

    # ── Pipeline checkpointer ─────────────────────────────────────────
    # False  → MemorySaver (in-process, lost on restart — suitable for dev/CI)
    # True   → SqliteSaver at checkpoints/pipeline_state.db (cross-restart resumability)
    use_persistent_checkpointer: bool = Field(
        default=False,
        description="Use SqliteSaver for cross-restart pipeline resumability.",
    )
    checkpoints_db_path: str = Field(
        default="checkpoints/pipeline_state.db",
        description="Path to the SQLite DB used by SqliteSaver.",
    )

    # ── Playwright ────────────────────────────────────────────────────
    # STAGING ONLY: True ignores invalid TLS certs on the staging domain.
    # Must be False in production to detect certificate issues.
    playwright_ignore_https_errors: bool = Field(
        default=False,
        description="STAGING ONLY — ignore TLS cert errors in Playwright. Never True in prod.",
    )

    @model_validator(mode="after")
    def _check_production_safety(self) -> "Settings":
        if self.env == "production" and self.playwright_ignore_https_errors:
            raise ValueError(
                "playwright_ignore_https_errors must be False in production "
                "(set ENV=production and PLAYWRIGHT_IGNORE_HTTPS_ERRORS=false)"
            )
        return self

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def telegram_channels(self) -> dict:
        return {
            "qa_leads": self.telegram_qa_leads_chat_id,
            "qa_team":  self.telegram_qa_team_chat_id,
            "qa_ops":   self.telegram_qa_ops_chat_id,
            "qa_bugs":  self.telegram_qa_bugs_chat_id,
        }


# Singleton — import this everywhere
settings = Settings()
