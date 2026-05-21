"""
Domain exception hierarchy for the QA AI framework.

All framework errors inherit from QAFrameworkError so callers can:
  - catch the base class for broad handling
  - catch a specific subclass for targeted recovery

Every exception carries an optional `context` dict for structured log attachment.
"""
from __future__ import annotations


class QAFrameworkError(Exception):
    """Base exception for all QA framework domain errors."""

    def __init__(self, message: str, context: dict | None = None) -> None:
        super().__init__(message)
        self.context: dict = context or {}


class LLMResponseError(QAFrameworkError):
    """Raised when an LLM response fails schema validation or is empty."""


class LLMRateLimitError(QAFrameworkError):
    """Raised when the LLM provider returns a rate-limit (429) response."""


class TestGenerationError(QAFrameworkError):
    """Raised when the AI fails to produce a valid test case or test plan."""


class JiraPostError(QAFrameworkError):
    """Raised when posting results back to Jira fails after retries."""


class PipelineStepError(QAFrameworkError):
    """Raised when a LangGraph pipeline node fails and cannot recover."""

    def __init__(self, message: str, node_name: str, context: dict | None = None) -> None:
        super().__init__(message, context)
        self.node_name = node_name


class WebhookValidationError(QAFrameworkError):
    """Raised when an inbound webhook payload fails schema or HMAC validation."""


class RAGRetrievalError(QAFrameworkError):
    """Raised when vector store retrieval fails or returns zero results."""


class CodeGenerationSecurityError(QAFrameworkError):
    """Raised when LLM-generated code fails AST security pre-flight."""


class POMRegistryError(QAFrameworkError):
    """Raised when a generated step references a method not in the POMRegistry."""
