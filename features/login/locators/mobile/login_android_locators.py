"""
Android Login Locators — single source of truth untuk semua element locators.
Menggunakan Flutter accessibility labels yang sudah diverifikasi dari app inspection.
"""

# ── Navigation ────────────────────────────────────────────────────────
ONBOARDING_LOGIN_LINK = "Already have an account? Log in"

# ── Login Form ────────────────────────────────────────────────────────
EMAIL_FIELD    = "Enter your email address"
PASSWORD_FIELD = "Enter your password"
LOGIN_BUTTON   = "Login to my account"

# ── Post-login ────────────────────────────────────────────────────────
FEED_SCREEN    = "HONO"

# ── Error States ──────────────────────────────────────────────────────
ERROR_KEYWORDS = ["invalid", "incorrect", "error", "wrong"]

# ── Element descriptions — untuk Self-Healer context ──────────────────
ELEMENT_DESCRIPTIONS = {
    "EMAIL_FIELD":    "Email input field on login screen",
    "PASSWORD_FIELD": "Password input field on login screen",
    "LOGIN_BUTTON":   "Login to my account button",
    "FEED_SCREEN":    "Feed/home screen after successful login",
}
