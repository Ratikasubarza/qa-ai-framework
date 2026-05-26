"""
POM Registry bootstrap — auto-discovers Page Objects and Screen Objects at session start.

Scans:
  features/*/pages/web/*_page.py       → web pages  (must subclass BasePage)
  features/*/screens/android/*_screen.py → android screens (must subclass BaseMobileScreen)

Import this module in conftest.py (session scope) as a side-effect import:
    import core.pom_registry_setup  # noqa: F401
"""
from __future__ import annotations

import importlib
import inspect
from pathlib import Path

import structlog

from core.pom_registry import registry

logger = structlog.get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _discover_web_pages() -> None:
    base_class_name = "BasePage"
    glob_pattern = "features/*/pages/web/*_page.py"

    for path in sorted(_PROJECT_ROOT.glob(glob_pattern)):
        feature = path.parts[path.parts.index("features") + 1]
        module_dotted = ".".join(path.relative_to(_PROJECT_ROOT).with_suffix("").parts)
        try:
            mod = importlib.import_module(module_dotted)
            for _, cls in inspect.getmembers(mod, inspect.isclass):
                if cls.__module__ != module_dotted:
                    continue
                bases = [b.__name__ for b in inspect.getmro(cls)[1:]]
                if base_class_name in bases:
                    registry.register_web_page(feature, cls)
                    break
        except Exception as e:
            logger.warning("pom_registry_web_skip", feature=feature, module=module_dotted, reason=str(e))


def _discover_mobile_screens() -> None:
    base_class_name = "BaseMobileScreen"

    for platform_dir in sorted((_PROJECT_ROOT / "features").glob("*/screens/*")):
        if not platform_dir.is_dir():
            continue
        feature = platform_dir.parts[platform_dir.parts.index("features") + 1]
        platform = platform_dir.name  # e.g. "android"

        for path in sorted(platform_dir.glob("*_screen.py")):
            module_dotted = ".".join(path.relative_to(_PROJECT_ROOT).with_suffix("").parts)
            try:
                mod = importlib.import_module(module_dotted)
                for _, cls in inspect.getmembers(mod, inspect.isclass):
                    if cls.__module__ != module_dotted:
                        continue
                    bases = [b.__name__ for b in inspect.getmro(cls)[1:]]
                    if base_class_name in bases:
                        registry.register_mobile_screen(feature, platform, cls)
                        break
            except Exception as e:
                logger.warning(
                    "pom_registry_mobile_skip",
                    feature=feature,
                    platform=platform,
                    module=module_dotted,
                    reason=str(e),
                )


def _register_all() -> None:
    _discover_web_pages()
    _discover_mobile_screens()

    logger.info(
        "pom_registry_bootstrapped",
        web_pages=registry.list_web_pages(),
        mobile_screens=registry.list_mobile_screens(),
    )


_register_all()
