"""
Login Page Locators — single source of truth for login page elements.
Priority order: data-testid > role > attribute > placeholder > CSS
All locators verified against app-dev.thehono.com
"""

# ── Form Fields ───────────────────────────────────────────────────────
EMAIL_FIELD    = 'input[type="email"]'
PASSWORD_FIELD = 'input[type="password"]'

# ── Buttons ───────────────────────────────────────────────────────────
LOGIN_BUTTON   = 'button[type="submit"]'

# ── Messages ──────────────────────────────────────────────────────────
ERROR_MESSAGE  = 'text=Invalid'
SUCCESS_URL    = "/feed"

# ── Element descriptions — used by Self-Healer for LLM context ───────
ELEMENT_DESCRIPTIONS = {
    "EMAIL_FIELD":    "Email input field on login form",
    "PASSWORD_FIELD": "Password input field on login form",
    "LOGIN_BUTTON":   "Submit/Login button on login form",
}

# ── Locator registry — used by Self-Healer for snapshot ───────────────
LOCATOR_REGISTRY = {
    "EMAIL_FIELD":    EMAIL_FIELD,
    "PASSWORD_FIELD": PASSWORD_FIELD,
    "LOGIN_BUTTON":   LOGIN_BUTTON,
}
