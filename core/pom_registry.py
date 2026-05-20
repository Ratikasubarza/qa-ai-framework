"""
POMRegistry — central registry of Page Object Model and Screen Object classes.

Provides a single lookup point so agents, healers, and pipeline nodes can
resolve a feature + platform to the correct class without hardcoded imports.

Usage:
    from core.pom_registry import registry

    PageClass = registry.get_web_page("login")
    ScreenClass = registry.get_mobile_screen("login", "android")
"""
from __future__ import annotations

from typing import Any

import structlog

from core.exceptions import POMRegistryError

logger = structlog.get_logger(__name__)


class POMRegistry:
    """Registry mapping feature keys to POM/Screen Object classes."""

    def __init__(self) -> None:
        self._web_pages:     dict[str, type] = {}
        self._mobile_screens: dict[str, dict[str, type]] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register_web_page(self, feature: str, page_class: type) -> None:
        """Register a Playwright Page Object class for a feature."""
        key = feature.lower()
        self._web_pages[key] = page_class
        logger.debug("pom_registry_web_registered", feature=key, cls=page_class.__name__)

    def register_mobile_screen(
        self, feature: str, platform: str, screen_class: type
    ) -> None:
        """Register an Appium Screen Object class for a feature + platform."""
        key     = feature.lower()
        plat    = platform.lower()
        self._mobile_screens.setdefault(key, {})[plat] = screen_class
        logger.debug(
            "pom_registry_mobile_registered",
            feature=key,
            platform=plat,
            cls=screen_class.__name__,
        )

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get_web_page(self, feature: str) -> type:
        """Return the registered web Page Object class for *feature*."""
        key = feature.lower()
        cls = self._web_pages.get(key)
        if cls is None:
            raise POMRegistryError(
                f"No web page registered for feature '{key}'.",
                context={"feature": key, "registered": list(self._web_pages.keys())},
            )
        return cls

    def get_mobile_screen(self, feature: str, platform: str = "android") -> type:
        """Return the registered mobile Screen Object class for *feature* + *platform*."""
        key  = feature.lower()
        plat = platform.lower()
        screens = self._mobile_screens.get(key, {})
        cls = screens.get(plat)
        if cls is None:
            raise POMRegistryError(
                f"No mobile screen registered for feature '{key}' / platform '{plat}'.",
                context={
                    "feature": key,
                    "platform": plat,
                    "registered": {k: list(v.keys()) for k, v in self._mobile_screens.items()},
                },
            )
        return cls

    # ── Introspection ─────────────────────────────────────────────────────────

    def list_web_pages(self) -> list[str]:
        return sorted(self._web_pages.keys())

    def list_mobile_screens(self) -> dict[str, list[str]]:
        return {k: sorted(v.keys()) for k, v in sorted(self._mobile_screens.items())}

    # ── Validation & export ───────────────────────────────────────────────────

    def validate_step(self, feature: str, platform: str, step: str) -> bool:
        """Return True if the registered POM/Screen class has a callable method *step*."""
        try:
            cls = (
                self.get_web_page(feature)
                if platform == "web"
                else self.get_mobile_screen(feature, platform)
            )
            return callable(getattr(cls, step, None))
        except POMRegistryError:
            return False

    def export_schema(self) -> dict[str, Any]:
        """Return a serialisable snapshot of all registered pages and screens."""
        return {
            "web_pages": {
                feat: {
                    "class": cls.__name__,
                    "module": cls.__module__,
                    "methods": [m for m in dir(cls) if not m.startswith("_")],
                }
                for feat, cls in self._web_pages.items()
            },
            "mobile_screens": {
                feat: {
                    plat: {
                        "class": cls.__name__,
                        "module": cls.__module__,
                        "methods": [m for m in dir(cls) if not m.startswith("_")],
                    }
                    for plat, cls in screens.items()
                }
                for feat, screens in self._mobile_screens.items()
            },
        }


registry = POMRegistry()
