"""
Reports Test Data — POST /v1/reports

Two interfaces:
  1. ReportTestData     (class constants) — static reference values
  2. ReportPayload      (dataclass)       — Builder pattern for parameterised tests
"""
from dataclasses import dataclass
from core.test_data.base_builder import PayloadBuilder


@dataclass
class ReportPayload(PayloadBuilder):
    subject:     str = "QA automated test report"
    report_type: str = "BUG"
    message:     str = "Automated test submission — please ignore."

    @classmethod
    def valid(cls) -> "ReportPayload":
        return cls()

    @classmethod
    def feedback(cls) -> "ReportPayload":
        return cls(report_type="FEEDBACK", subject="QA feedback report", message="Feedback from automated test.")

    @classmethod
    def invalid_type(cls) -> "ReportPayload":
        return cls(report_type="INVALID_TYPE")

    @classmethod
    def missing_message(cls) -> dict:
        return cls().without("message")

    @classmethod
    def missing_subject(cls) -> dict:
        return cls().without("subject")

    @classmethod
    def missing_type(cls) -> dict:
        return cls().without("report_type")

    @classmethod
    def empty_subject(cls) -> "ReportPayload":
        return cls(subject="")

    @classmethod
    def long_message(cls, length: int = 5000) -> "ReportPayload":
        return cls(message="A" * length)


class ReportTestData:
    # Expected response values
    SUCCESS_CODE    = "OK"
    SUCCESS_MESSAGE = "Data saved"

    # Valid report_type values
    TYPE_BUG        = "BUG"
    TYPE_FEEDBACK   = "FEEDBACK"
    TYPE_OTHER      = "OTHER"
    TYPE_INVALID    = "INVALID_TYPE"

    # Expected error response codes
    ERROR_UNPROCESSABLE = "NOKUNPROC"

    # Response schema keys
    REQUIRED_RESPONSE_KEYS = {"id", "subject", "report_type", "created_at"}

    # Performance SLA
    MAX_RESPONSE_MS = 3000
