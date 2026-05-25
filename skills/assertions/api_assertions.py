"""
DEPRECATED — use skills.api.schema_validator.SchemaValidator instead.

APIAssertions is an alias kept only for backward-compatibility during the
migration period. It will be removed once all test files are updated.

Canonical import:
    from skills.api.schema_validator import SchemaValidator
"""
import warnings

warnings.warn(
    "skills.assertions.api_assertions is deprecated. "
    "Import from skills.api.schema_validator directly: "
    "from skills.api.schema_validator import SchemaValidator",
    DeprecationWarning,
    stacklevel=2,
)

from skills.api.schema_validator import SchemaValidator as APIAssertions

__all__ = ["APIAssertions"]
