import yaml
import time
import structlog
from enum import Enum
from pathlib import Path
from openai import OpenAI
from core.secret_manager import secret_manager

logger = structlog.get_logger(__name__)

FALLBACK_MODELS = {
    "fast": [
        "nvidia/nemotron-nano-9b-v2:free",
        "meta-llama/llama-3.2-3b-instruct:free",
        "liquid/lfm-2.5-1.2b-instruct:free",
        "openai/gpt-oss-20b:free",
    ],
    "standard": [
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "openai/gpt-oss-20b:free",
        "openai/gpt-oss-120b:free",
    ],
    "complex": [
        "openai/gpt-oss-120b:free",
        "openai/gpt-oss-20b:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "meta-llama/llama-3.3-70b-instruct:free",
    ],
}

class ModelTier(str, Enum):
    FAST     = "fast"
    STANDARD = "standard"
    COMPLEX  = "complex"

class LLMResponse:
    def __init__(self, content: str, model: str, tokens_used: int):
        self.content     = content
        self.model       = model
        self.tokens_used = tokens_used
    def __str__(self):
        return self.content

class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=secret_manager.get("openrouter_api_key"),
            base_url=secret_manager.get("openrouter_base_url"),
        )
        logger.info("llm_client_ready", provider="openrouter")

    def complete(
        self,
        messages:   list,
        tier:       ModelTier = ModelTier.STANDARD,
        agent_name: str = "",
        json_mode:  bool = False,
    ) -> LLMResponse:
        models     = FALLBACK_MODELS.get(tier.value, FALLBACK_MODELS["standard"])
        last_error = None

        for model in models:
            try:
                kwargs = dict(
                    model=model,
                    messages=messages,
                    max_tokens=16000,
                    temperature=0.2,
                )
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                logger.info("llm_request", agent=agent_name, tier=tier.value, model=model)
                response = self.client.chat.completions.create(**kwargs)
                content  = response.choices[0].message.content
                tokens   = response.usage.total_tokens if response.usage else 0
                logger.info("llm_response", agent=agent_name, tokens=tokens, model=model)

                return LLMResponse(content=content, model=model, tokens_used=tokens)

            except Exception as e:
                logger.warning("llm_fallback", model=model, error=str(e)[:80])
                last_error = e
                time.sleep(3)
                continue

        raise last_error

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
