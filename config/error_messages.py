"""
Centralized error/validation message strings — single source of truth.
Usage: from config.error_messages import APIErrors, AndroidErrors, ValidationErrors
"""


class APIErrors:
    """API response error codes and messages."""

    # ── Auth ──────────────────────────────────────────────────────────
    UNAUTHORIZED        = "Unauthorized"
    INVALID_CREDENTIALS = "Invalid credentials"
    TOKEN_MISSING       = "Token missing"
    API_KEY_MISSING     = "API key missing"

    # ── Register ──────────────────────────────────────────────────────
    EMAIL_ALREADY_REGISTERED = "Email already registered"
    PHONE_ALREADY_REGISTERED = "Phone number already registered"
    EMAIL_FORMAT_INVALID     = "Invalid email format"

    # ── Generic ───────────────────────────────────────────────────────
    NOT_FOUND           = "Not found"
    INTERNAL_ERROR      = "Internal server error"
    VALIDATION_FAILED   = "Validation failed"

    # ── Success codes ─────────────────────────────────────────────────
    SUCCESS_CODE        = "OK"


class ValidationErrors:
    """Field validation messages returned in 400/422 responses."""

    REQUIRED_FIELD      = "required"
    INVALID_FORMAT      = "invalid"
    TOO_LONG            = "too long"
    TOO_SHORT           = "too short"
    DUPLICATE           = "already"


class AndroidErrors:
    """Android toast and UI error text patterns — used with `in source.lower()`."""

    INVALID_CREDENTIALS = ["invalid", "incorrect", "wrong", "error"]
    ALREADY_EXISTS      = ["error", "already", "exist", "duplicate"]
    NETWORK_ERROR       = ["network", "connection", "timeout"]
    VERIFY_EMAIL_SCREEN = "Please verify your email"
    OPEN_EMAIL_BTN      = "Open email app"
