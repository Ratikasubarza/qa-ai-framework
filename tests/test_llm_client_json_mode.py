"""
Unit tests for SUPPORTS_JSON_MODE prefix matching in LLMClient.

Tests the matching logic in isolation — no LLM calls, no network.
"""
import pytest
from core.llm_client import SUPPORTS_JSON_MODE


def _matches(model: str) -> bool:
    """Mirror of the production matching expression in _call_model."""
    return any(m in model for m in SUPPORTS_JSON_MODE)


# ── Matched models (json_mode IS applied) ─────────────────────────────────────

@pytest.mark.parametrize("model", [
    "openai/gpt-oss-20b:free",
    "openai/gpt-oss-120b:free",
    "openai/gpt-4-turbo",
    "openai/gpt-3.5-turbo",
    "anthropic/claude-sonnet-4-5",
    "anthropic/claude-haiku-4-5-20251001",
    "anthropic/claude-opus-4-5",
    "deepseek/deepseek-r1-0528:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "liquid/lfm-2.5-1.2b-instruct:free",
])
def test_matched_models_support_json_mode(model: str):
    assert _matches(model), (
        f"Model '{model}' should match SUPPORTS_JSON_MODE but did not. "
        f"Add its vendor prefix to the list."
    )


# ── Unmatched models (json_mode is silently ignored) ─────────────────────────

@pytest.mark.parametrize("model", [
    "google/gemini-pro",
    "google/gemini-flash-1.5",
    "cohere/command-r-plus",
    "ai21/jamba-1.5-large",
    "perplexity/llama-3-sonar-large",
    "x-ai/grok-2",
])
def test_unmatched_models_do_not_support_json_mode(model: str):
    assert not _matches(model), (
        f"Model '{model}' should NOT match SUPPORTS_JSON_MODE but did. "
        f"Prefix too broad — tighten the list."
    )


# ── Partial-prefix edge cases ─────────────────────────────────────────────────

def test_prefix_does_not_match_partial_vendor():
    """'openai/gpt-oss' must not accidentally match an unrelated string."""
    assert not _matches("openai/gpt-oss-competitor-fork:free".replace("openai/gpt-oss", "fakecorp/gpt-oss"))

def test_llama_3_prefix_matches_llama_3_dot_x():
    """'meta-llama/llama-3' must match llama-3.2 and llama-3.3 variants."""
    assert _matches("meta-llama/llama-3.2-3b-instruct:free")
    assert _matches("meta-llama/llama-3.3-70b-instruct:free")

def test_hermes_prefix_does_not_match_hermes_2():
    """'nousresearch/hermes-3' must NOT match hermes-2 (different model family)."""
    assert not _matches("nousresearch/hermes-2-llama-3.1-405b")

def test_deepseek_r1_prefix_matches_dated_variants():
    """'deepseek/deepseek-r1' must match deepseek-r1-0528 and similar."""
    assert _matches("deepseek/deepseek-r1-0528:free")
    assert _matches("deepseek/deepseek-r1")

def test_deepseek_r1_prefix_does_not_match_r2():
    """'deepseek/deepseek-r1' must NOT match a hypothetical deepseek-r2."""
    assert not _matches("deepseek/deepseek-r2-0528:free")


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_model_string_does_not_match():
    assert not _matches("")

def test_whitespace_model_string_does_not_match():
    assert not _matches("   ")

def test_json_mode_prefix_list_is_nonempty():
    assert len(SUPPORTS_JSON_MODE) >= 11, (
        "SUPPORTS_JSON_MODE shrank below the expected 11 entries — accidental deletion?"
    )
