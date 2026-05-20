"""
Android Login Locators — verified dari app inspection.
Flutter app menggunakan android.widget.EditText untuk input fields.
"""
from appium.webdriver.common.appiumby import AppiumBy

# ── Navigation ────────────────────────────────────────────────────────
ONBOARDING_LOGIN_LINK = "Already have an account? Log in"

# ── Login Form — semantic accessibility IDs (preferred)
# Flutter Semantics labels are exposed as content-desc via UIAutomator.
EMAIL_FIELD_AID    = "Email"     # content-desc / Semantics label
PASSWORD_FIELD_AID = "Password"  # content-desc / Semantics label

# ── Login Form — class name (used for element-wait in ensure_on_login_screen)
EMAIL_FIELD_CLASS    = "android.widget.EditText"

# ── Buttons ───────────────────────────────────────────────────────────
LOGIN_BUTTON   = "Login to my account"
APPLY_BUTTON   = "Apply to join"

# ── Post-login screens ────────────────────────────────────────────────
FEED_SCREEN    = "Home"  # Bottom nav Home tab — indicates feed screen

# ── Bottom navigation tabs ────────────────────────────────────────────
TAB_HOME          = "Home"
TAB_NETWORK       = "Network"
TAB_COMMUNITIES   = "Communities"
TAB_NOTIFICATIONS = "Notifications"
TAB_MESSAGES      = "Messages"

# ── Feed filters ──────────────────────────────────────────────────────
FILTER_ALL       = "All"
FILTER_FOLLOWING = "Following"

# ── Element descriptions ──────────────────────────────────────────────
ELEMENT_DESCRIPTIONS = {
    "EMAIL_FIELD":    "Email input (EditText index 0)",
    "PASSWORD_FIELD": "Password input (EditText index 1)",
    "LOGIN_BUTTON":   "Login to my account button",
    "FEED_SCREEN":    "HONO header on feed screen",
}
# ── Profile menu ──────────────────────────────────────────────────────
AVATAR_X         = 50    # x coordinate of avatar button
AVATAR_Y         = 120   # y coordinate of avatar button
SHOW_MENU        = "Show menu"
LOGOUT_BUTTON    = "Logout"

# ── Profile screen ────────────────────────────────────────────────────
MY_PROFILE       = "My Profile"
SETTINGS         = "Settings & Preference"
REPORT_FEEDBACK  = "Report & Feedback"
