"""
LLM client — single abstraction over OpenRouter (development) and Claude (production).

Retry strategy: tenacity exponential backoff per model attempt.
Fallback strategy: iterate through the tier's model list; raise LLMResponseError
after all models are exhausted.
"""
from __future__ import annotations

import os
from enum import Enum

import structlog
from openai import OpenAI, RateLimitError as OpenAIRateLimitError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.exceptions import LLMRateLimitError, LLMResponseError
from core.secret_manager import secret_manager

logger = structlog.get_logger(__name__)

ACTIVE_TIER = os.getenv("MODEL_TIER", "development")  # development | production

FALLBACK_MODELS: dict[str, list[str]] = {
    # ── Development — free models via OpenRouter ───────────────────────
    "fast": [
        "nvidia/nemotron-nano-9b-v2:free",
        "meta-llama/llama-3.2-3b-instruct:free",
        "liquid/lfm-2.5-1.2b-instruct:free",
        "openai/gpt-oss-20b:free",
    ],
    "standard": [
        "openai/gpt-oss-20b:free",
        "openai/gpt-oss-120b:free",
        "deepseek/deepseek-r1-0528:free",
        "mistralai/mistral-small-3.1-24b-instruct:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
    ],
    "complex": [
        "openai/gpt-oss-120b:free",
        "openai/gpt-oss-20b:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "meta-llama/llama-3.3-70b-instruct:free",
    ],
    # ── Production — Claude models (activate with MODEL_TIER=production) ──
    "production_fast": [
        "anthropic/claude-haiku-4-5",
        "anthropic/claude-haiku-4-5-20251001",
    ],
    "production_standard": [
        "anthropic/claude-sonnet-4-5",
        "anthropic/claude-sonnet-4-5-20250514",
    ],
    "production_complex": [
        "anthropic/claude-opus-4-5",
        "anthropic/claude-sonnet-4-5-20250514",
    ],
}

SUPPORTS_JSON_MODE: list[str] = [
    "openai/gpt-4",
    "openai/gpt-3.5",
    "anthropic/claude",
]


class ModelTier(str, Enum):
    FAST     = "fast"
    STANDARD = "standard"
    COMPLEX  = "complex"


class LLMResponse:
    def __init__(self, content: str, model: str, tokens_used: int) -> None:
        self.content     = content
        self.model       = model
        self.tokens_used = tokens_used

    def __str__(self) -> str:
        return self.content


class LLMClient:
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=secret_manager.get("openrouter_api_key"),
            base_url=secret_manager.get("openrouter_base_url"),
        )
        logger.info("llm_client_ready", provider="openrouter")

    # ── Internal: single model call with exponential backoff ─────────────────

    def _call_model(
        self,
        model: str,
        messages: list[dict],
        json_mode: bool = False,
    ) -> LLMResponse:
        """Call one model.  Raises LLMRateLimitError on 429, raw Exception otherwise."""
        kwargs: dict = dict(
            model=model,
            messages=messages,
            max_tokens=16000,
            temperature=0.2,
        )
        if json_mode and any(m in model for m in SUPPORTS_JSON_MODE):
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(**kwargs)
        except OpenAIRateLimitError as exc:
            # Translate provider 429 → typed domain exception so tenacity can target it
            raise LLMRateLimitError(
                f"Rate limited by {model}",
                context={"model": model, "error": str(exc)},
            ) from exc

        content = response.choices[0].message.content or ""
        tokens  = response.usage.total_tokens if response.usage else 0
        return LLMResponse(content=content, model=model, tokens_used=tokens)

    def _call_model_with_backoff(
        self,
        model: str,
        messages: list[dict],
        json_mode: bool = False,
    ) -> LLMResponse:
        """Wrap _call_model in tenacity backoff targeting transient errors only."""

        @retry(
            retry=retry_if_exception_type((LLMRateLimitError, ConnectionError, TimeoutError)),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            before_sleep=before_sleep_log(logger, logging.WARNING),  # type: ignore[arg-type]
            reraise=True,
        )
        def _inner() -> LLMResponse:
            return self._call_model(model, messages, json_mode)

        return _inner()

    # ── Public API ────────────────────────────────────────────────────────────

    def complete(
        self,
        messages:   list[dict],
        tier:       ModelTier = ModelTier.STANDARD,
        agent_name: str = "",
        json_mode:  bool = False,
    ) -> LLMResponse:
        """
        Try each model in the tier's fallback list with exponential backoff.
        Moves to the next model on rate-limit; raises LLMResponseError when
        all models in the tier are exhausted.
        """
        models     = FALLBACK_MODELS.get(tier.value, FALLBACK_MODELS["standard"])
        last_error: Exception | None = None

        for model in models:
            try:
                logger.info("llm_request", agent=agent_name, tier=tier.value, model=model)
                result = self._call_model_with_backoff(model, messages, json_mode)
                logger.info(
                    "llm_response",
                    agent=agent_name,
                    tokens=result.tokens_used,
                    model=result.model,
                )
                return result

            except LLMRateLimitError:
                logger.warning("llm_rate_limited_moving_to_next", model=model, agent=agent_name)
                last_error = LLMRateLimitError(f"Rate limit exhausted for {model}")
                continue

            except Exception as exc:
                logger.warning("llm_model_failed", model=model, error=str(exc)[:120])
                last_error = exc
                continue

        raise LLMResponseError(
            f"All LLM fallback models in tier '{tier.value}' failed.",
            context={"tier": tier.value, "models": models, "last_error": str(last_error)},
        ) from last_error

    def complete_text(
        self,
        system:     str,
        user:       str,
        tier:       ModelTier = ModelTier.STANDARD,
        agent_name: str = "",
        json_mode:  bool = False,
    ) -> LLMResponse:
        return self.complete(
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            tier=tier,
            agent_name=agent_name,
            json_mode=json_mode,
        )


llm_client = LLMClient()
