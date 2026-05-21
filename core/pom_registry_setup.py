"""
POM Registry bootstrap — call once at session start to register all Page Objects
and Screen Objects into the central registry.

Import this module in conftest.py (session scope) so every test has access to
the registry without each test file importing concrete page classes directly.

Usage (conftest.py):
    import core.pom_registry_setup  # noqa: F401  — side-effect import
"""
from __future__ import annotations

import structlog

from core.pom_registry import registry

logger = structlog.get_logger(__name__)


def _register_all() -> None:
    # ── Web Page Objects ──────────────────────────────────────────────────────
    try:
        from features.login.pages.web.login_page import LoginPage
        registry.register_web_page("login", LoginPage)
    except ImportError as e:
        logger.warning("pom_registry_web_skip", feature="login", reason=str(e))

    # ── Mobile Screen Objects (Android) ───────────────────────────────────────
    try:
        from features.login.screens.android.login_screen import LoginScreen
        registry.register_mobile_screen("login", "android", LoginScreen)
    except ImportError as e:
        logger.warning("pom_registry_mobile_skip", feature="login", platform="android", reason=str(e))

    logger.info(
        "pom_registry_bootstrapped",
        web_pages=registry.list_web_pages(),
        mobile_screens=registry.list_mobile_screens(),
    )


_register_all()
