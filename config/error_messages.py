"""
Centralized error/validation message strings — single source of truth.
Usage: from config.error_messages import APIErrors, APICodes, APIEnums, ValidationErrors, AndroidErrors
"""


class APICodes:
    """API response 'code' field values."""

    # ── Success ───────────────────────────────────────────────────────────
    OK                  = "OK"

    # ── Business error codes ──────────────────────────────────────────────
    NOKUNPROC           = "NOKUNPROC"   # Unprocessable — duplicate / conflict / unknown value
    EXPIRED             = "EXPIRED"     # Verification / reset link has expired


class APIMessages:
    """API response 'message' field values."""

    # ── Success messages ──────────────────────────────────────────────────
    DATA_SAVED          = "Data saved"
    DATA_FOUND          = "Data found"
    DATA_DELETED        = "Data deleted"

    # ── Auth / account ────────────────────────────────────────────────────
    UNAUTHORIZED            = "Unauthorized"
    INVALID_CREDENTIALS     = "Invalid credentials"
    TOKEN_MISSING           = "Token missing"
    API_KEY_MISSING         = "API key missing"
    EXPIRED_LINK            = "Verification link has expired"

    # ── Register / email ──────────────────────────────────────────────────
    EMAIL_ALREADY_EXISTS    = "email already exists"
    EMAIL_ALREADY_REGISTERED = "Email already registered"
    EMAIL_UPDATED           = "Email updated successfully"
    PHONE_ALREADY_REGISTERED = "Phone number already registered"
    EMAIL_FORMAT_INVALID    = "Invalid email format"

    # ── Account / phone ───────────────────────────────────────────────────
    UNKNOWN_PHONE_CODE      = "unknown country phone code"

    # ── Posts ─────────────────────────────────────────────────────────────
    AT_LEAST_ONE_TOPIC      = "at least 1 topic is required"
    MENTION_BLOCKED         = "user does not allow mentions from you"

    # ── Admin moderation ──────────────────────────────────────────────────
    ALREADY_HIDDEN          = "already hidden"
    NOT_HIDDEN              = "not hidden"

    # ── Generic ───────────────────────────────────────────────────────────
    NOT_FOUND               = "Not found"
    INTERNAL_ERROR          = "Internal server error"
    VALIDATION_FAILED       = "Validation failed"


class APIErrors:
    """Backward-compatible alias — use APIMessages for new code."""

    UNAUTHORIZED            = APIMessages.UNAUTHORIZED
    INVALID_CREDENTIALS     = APIMessages.INVALID_CREDENTIALS
    TOKEN_MISSING           = APIMessages.TOKEN_MISSING
    API_KEY_MISSING         = APIMessages.API_KEY_MISSING
    EMAIL_ALREADY_REGISTERED = APIMessages.EMAIL_ALREADY_REGISTERED
    PHONE_ALREADY_REGISTERED = APIMessages.PHONE_ALREADY_REGISTERED
    EMAIL_FORMAT_INVALID    = APIMessages.EMAIL_FORMAT_INVALID
    NOT_FOUND               = APIMessages.NOT_FOUND
    INTERNAL_ERROR          = APIMessages.INTERNAL_ERROR
    VALIDATION_FAILED       = APIMessages.VALIDATION_FAILED
    SUCCESS_CODE            = APICodes.OK


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
