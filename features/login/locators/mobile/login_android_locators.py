"""
Android Login Locators — verified dari app inspection.
Flutter app menggunakan android.widget.EditText untuk input fields.
"""
from appium.webdriver.common.appiumby import AppiumBy

# ── Navigation ────────────────────────────────────────────────────────
ONBOARDING_LOGIN_LINK = "Already have an account? Log in"

# ── Login Form — pakai EditText index karena Flutter tidak expose resource-id
EMAIL_FIELD_CLASS    = "android.widget.EditText"
EMAIL_FIELD_INDEX    = 0   # first EditText
PASSWORD_FIELD_INDEX = 1   # second EditText (password=true)

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
