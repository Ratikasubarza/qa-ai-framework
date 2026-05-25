"""
API contract enum values — string constants sent in request/response bodies.
Usage: from config.api_enums import ReportCategory, ModerationStatus, SettingsSection, MessagePreference, Visibility
"""


class ReportCategory:
    SPAM        = "SPAM"
    BUG         = "BUG"
    HARASSMENT  = "HARASSMENT"


class ModerationStatus:
    PENDING     = "PENDING"
    HIDDEN      = "HIDDEN"
    DISMISSED   = "DISMISSED"


class AccountSection:
    BLOCKED     = "BLOCKED"
    MUTED       = "MUTED"


class SettingsSection:
    PERSONAL        = "PERSONAL"
    NOTIFICATION    = "NOTIFICATION"
    AUDIENCE        = "AUDIENCE"
    MESSAGE         = "MESSAGE"


class MessagePreference:
    NO_ONE          = "NO_ONE"
    VERIFIED_USER   = "VERIFIED_USER"
    EVERYONE        = "EVERYONE"


class AudiencePreference:
    NO_ONE          = "NO_ONE"
    FOLLOWERS_ONLY  = "FOLLOWERS_ONLY"
    EVERYONE        = "EVERYONE"


class Visibility:
    EVERYONE        = "EVERYONE"
    FOLLOWERS_ONLY  = "FOLLOWERS_ONLY"
