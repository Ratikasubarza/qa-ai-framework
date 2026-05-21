"""
Locator registry loader — reads YAML metadata files for the locator_agent and self_healer.

These YAML files are METADATA ONLY. The Python locator files in features/*/locators/
remain the runtime source of truth. YAML adds: fallbacks, confidence, healing history.

Usage:
    from locators.registry.loader import load_locator_registry

    registry = load_locator_registry("login", "web")
    # -> list of locator dicts with primary, fallbacks, confidence, healing_history
"""
from __future__ import annotations

import yaml
import structlog
from pathlib import Path
from typing import Any

logger = structlog.get_logger(__name__)

REGISTRY_DIR = Path(__file__).parent


def load_locator_registry(feature: str, platform: str) -> list[dict[str, Any]]:
    """
    Load YAML locator metadata for a feature+platform combination.

    Returns list of locator dicts, empty list if file not found.
    """
    filename = f"{feature}.{platform}.yaml"
    path = REGISTRY_DIR / filename
    if not path.exists():
        logger.debug("locator_registry_not_found", feature=feature, platform=platform)
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        locators = data.get("locators", [])
        logger.info(
            "locator_registry_loaded",
            feature=feature,
            platform=platform,
            count=len(locators),
        )
        return locators
    except Exception as e:
        logger.error("locator_registry_load_failed", path=str(path), error=str(e))
        return []


def record_healing(
    feature:  str,
    platform: str,
    locator_name: str,
    old_value:    str,
    new_value:    str,
    confidence:   float,
    reason:       str,
) -> bool:
    """
    Append a healing event to the YAML file for a locator.
    Returns True if the file was updated, False if not found.

    Self-healer MUST call this after a successful heal so the team can audit
    what changed, when, and why. This is the paper trail for locator changes.
    """
    from datetime import datetime

    filename = f"{feature}.{platform}.yaml"
    path = REGISTRY_DIR / filename
    if not path.exists():
        logger.warning("locator_registry_missing_for_heal", feature=feature, platform=platform)
        return False

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for locator in data.get("locators", []):
            if locator.get("name") == locator_name:
                event = {
                    "date":       datetime.now().strftime("%Y-%m-%d"),
                    "old_value":  old_value,
                    "new_value":  new_value,
                    "confidence": round(confidence, 3),
                    "reason":     reason,
                }
                if "healing_history" not in locator:
                    locator["healing_history"] = []
                locator["healing_history"].append(event)
                locator["primary"]    = new_value
                locator["confidence"] = round(confidence, 3)
                locator["last_verified"] = datetime.now().strftime("%Y-%m-%d")
                break
        path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        logger.info(
            "locator_healing_recorded",
            feature=feature,
            platform=platform,
            locator=locator_name,
            confidence=confidence,
        )
        return True
    except Exception as e:
        logger.error("locator_healing_record_failed", error=str(e))
        return False


def list_registries() -> list[str]:
    """Return list of registered feature.platform combinations."""
    return [
        p.stem
        for p in sorted(REGISTRY_DIR.glob("*.yaml"))
        if p.stem not in ("schema", "__init__")
    ]
