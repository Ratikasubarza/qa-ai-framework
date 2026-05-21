"""
Login Page Locators — single source of truth for login page elements.
Priority order: role > label > placeholder > CSS attribute
All locators verified against app-dev.thehono.com

Preferred: role-based locators via page.get_by_role() / page.get_by_label()
Fallback:  CSS attribute selectors kept for self-healer snapshot context
"""

# ── Semantic role specs — use with BasePage.get_by_role() / page.get_by_label()
EMAIL_LABEL       = "Email"              # page.get_by_label("Email")
PASSWORD_LABEL    = "Password"           # page.get_by_label("Password")
LOGIN_BUTTON_NAME = "Login to my account"  # page.get_by_role("button", name=...)

# ── CSS fallback — kept for Self-Healer snapshot and wait_for() compatibility
EMAIL_FIELD    = 'input[type="email"]'
PASSWORD_FIELD = 'input[type="password"]'
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
