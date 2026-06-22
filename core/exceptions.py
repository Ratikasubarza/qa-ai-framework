"""Custom exceptions for qa-ai-framework."""


class LLMRateLimitError(Exception):
    """Raised when the LLM provider returns a rate-limit response."""


class LLMResponseError(Exception):
    """Raised when the LLM returns an unparseable or empty response."""


class CodeGenerationSecurityError(Exception):
    """Raised when generated code fails the AST security pre-flight check."""

    def __init__(self, message: str, context: dict | None = None):
        super().__init__(message)
        self.context = context or {}


class WebhookValidationError(Exception):
    """Raised when a webhook payload fails HMAC or schema validation."""


class POMRegistryError(Exception):
    """Raised when a POM/Screen class cannot be found in the registry."""
