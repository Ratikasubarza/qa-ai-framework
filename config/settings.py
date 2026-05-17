from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
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

    # ── ChromaDB ──────────────────────────────────────────
    hono_api_url:     str = "https://api-dev.thehono.com"
    hono_web_url:     str = "https://dev.thehono.com"
    hono_cms_url:     str = "https://cms-dev.thehono.com"
    hono_api_key:     str = Field("", description="Hono API key from environment")
    staging_email:    str = Field("", description="Staging account email from environment")
    staging_password: str = Field("", description="Staging account password from environment")
    staging_cms_email: str = Field("", description="CMS account email from environment")
    staging_cms_password: str = Field("", description="CMS account password from environment")
    chroma_persist_dir: str = "./knowledge_base/vector_store"

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
