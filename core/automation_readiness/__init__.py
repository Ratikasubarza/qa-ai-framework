"""Automation readiness gate for safe code generation."""

from core.automation_readiness.checker import check_automation_readiness
from core.automation_readiness.evidence import (
    load_automation_evidence,
    normalize_automation_evidence,
)

__all__ = [
    "check_automation_readiness",
    "load_automation_evidence",
    "normalize_automation_evidence",
]
