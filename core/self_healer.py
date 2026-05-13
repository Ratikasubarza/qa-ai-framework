"""
Self Healer — orchestrates locator healing pipeline.
"""
import ast
import re
import shutil
import structlog
from datetime import datetime
from pathlib import Path
from playwright.sync_api import Page

from agents.locator_agent import locator_agent
from knowledge_base.locator_store import locator_store
from core import input_sanitizer

logger = structlog.get_logger(__name__)

SNAPSHOT_DIR = Path("reports/locator_snapshots")
DEBUG_DIR    = Path("reports/debug_logs")


class HealResult:
    def __init__(self, healed, applied, candidates, snapshot_id, feature, element):
        self.healed      = healed
        self.applied     = applied
        self.candidates  = candidates
        self.snapshot_id = snapshot_id
        self.feature     = feature
        self.element     = element
        self.healed_at   = datetime.now()


class SelfHealer:
    def __init__(self):
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    def heal(self, page, feature, element, broken_locator, locators_file=None):
        logger.info("self_heal_start", feature=feature, element=element, broken=broken_locator)

        snapshot_id  = self._create_snapshot(feature, locators_file)
        dom_snapshot = self._capture_dom(page)
        self._capture_screenshot(page, feature, element)

        clean_dom  = input_sanitizer.sanitize(dom_snapshot, source=f"dom/{feature}")
        candidates = locator_agent.suggest(
            broken_locator=broken_locator,
            element_description=f"{element} on {feature} page",
            dom_snapshot=clean_dom.content,
        )

        if not candidates:
            logger.warning("no_candidates", feature=feature, element=element)
            return HealResult(False, None, [], snapshot_id, feature, element)

        for i, candidate in enumerate(candidates):
            locator_str = candidate.get("locator", "")
            if not locator_str:
                continue

            locator_str = self._normalize_locator(locator_str)
            logger.info("trying_candidate", attempt=i+1, locator=locator_str)

            if self._try_locator(page, locator_str):
                if self._smoke_test(page, locator_str):
                    locator_store.save(feature=feature, element=element, locator=locator_str, success=True)
                    if locators_file:
                        self._update_locators_file(locators_file, element, broken_locator, locator_str)
                    logger.info("self_heal_success", healed_locator=locator_str)
                    return HealResult(True, locator_str, candidates, snapshot_id, feature, element)
                else:
                    self._restore_snapshot(snapshot_id, locators_file)

        # LLM candidates failed — try common CSS fallbacks
        FALLBACKS = {
            "email": ['input[type="email"]', 'input[name="email"]', 'input[id*="email"]'],
            "password": ['input[type="password"]', 'input[name="password"]'],
            "button": ['button[type="submit"]', 'button:has-text("Login")', 'button:has-text("Sign in")'],
        }
        element_lower = element.lower()
        for key, fallbacks in FALLBACKS.items():
            if key in element_lower:
                for fb in fallbacks:
                    if self._try_locator(page, fb):
                        logger.info("fallback_healed", locator=fb)
                        locator_store.save(feature=feature, element=element, locator=fb, success=True)
                        return HealResult(True, fb, candidates, snapshot_id, feature, element)

        logger.error("self_heal_failed", candidates_tried=len(candidates))
        for c in candidates:
            locator_store.save(feature=feature, element=element, locator=c.get("locator",""), success=False)

        return HealResult(False, None, candidates, snapshot_id, feature, element)

    def _normalize_locator(self, locator):
        """Fix LLM locator syntax issues."""
        # Fix JS object syntax: { name: 'X' } -> name="X"
        locator = re.sub(r'\{\s*name:\s*["\'](.+?)["\']\s*\}', r'name="\1"', locator)
        locator = re.sub(r'\{\s*(\w+):\s*["\'](.+?)["\']\s*\}', r'\1="\2"', locator)
        # Fix get_by_test_id -> CSS selector
        m = re.search(r"get_by_test_id\(['\"](.+?)['\"]\)", locator)
        if m:
            return f'[data-testid="{m.group(1)}"]'
        return locator

    def _resolve_playwright_locator(self, page: Page, locator: str):
        """
        Resolve a limited set of Playwright locator expressions without eval.

        The locator agent may suggest strings like
        page.get_by_role("button", name="Continue"). We parse only known
        get_by_* calls and reject anything else so LLM output cannot execute
        arbitrary Python.
        """
        match = re.fullmatch(r"page\.(get_by_[a-z_]+)\((.*)\)", locator.strip())
        if not match:
            return None

        method_name, args_source = match.groups()
        allowed_methods = {
            "get_by_alt_text",
            "get_by_label",
            "get_by_placeholder",
            "get_by_role",
            "get_by_test_id",
            "get_by_text",
            "get_by_title",
        }
        if method_name not in allowed_methods or not hasattr(page, method_name):
            return None

        try:
            parsed = ast.parse(f"f({args_source})", mode="eval")
        except SyntaxError:
            return None

        call = parsed.body
        if not isinstance(call, ast.Call):
            return None

        args = []
        kwargs = {}
        allowed_kwarg_names = {"checked", "disabled", "exact", "expanded", "include_hidden", "level", "name", "pressed", "selected"}
        for arg in call.args:
            try:
                args.append(ast.literal_eval(arg))
            except (ValueError, SyntaxError):
                return None
        for keyword in call.keywords:
            if keyword.arg not in allowed_kwarg_names:
                return None
            try:
                kwargs[keyword.arg] = ast.literal_eval(keyword.value)
            except (ValueError, SyntaxError):
                return None

        return getattr(page, method_name)(*args, **kwargs)

    def _try_locator(self, page, locator, timeout=3000):
        try:
            if locator.startswith("page.get_by"):
                el = self._resolve_playwright_locator(page, locator)
                if el is None:
                    return False
                el.wait_for(timeout=timeout)
            elif locator.startswith("[") or locator.startswith("input") or locator.startswith("button"):
                page.wait_for_selector(locator, timeout=timeout)
            elif "=" in locator and not locator.startswith("["):
                page.wait_for_selector(f"[{locator}]", timeout=timeout)
            else:
                page.wait_for_selector(locator, timeout=timeout)
            return True
        except Exception:
            return False

    def _smoke_test(self, page, locator):
        try:
            if locator.startswith("page.get_by"):
                el = self._resolve_playwright_locator(page, locator)
                if el is None:
                    return False
                return el.is_visible()
            elif "=" in locator and not locator.startswith("[") and not locator.startswith("input") and not locator.startswith("button"):
                return page.is_visible(f"[{locator}]")
            return page.is_visible(locator)
        except Exception:
            return False

    def _capture_screenshot(self, page, feature, element):
        path = DEBUG_DIR / f"heal_{feature}_{element}_{datetime.now().strftime('%H%M%S')}.png"
        try:
            page.screenshot(path=str(path))
        except Exception as e:
            logger.warning("screenshot_failed", error=str(e))
        return str(path)

    def _capture_dom(self, page):
        try:
            return page.content()[:5000]
        except Exception:
            return ""

    def _create_snapshot(self, feature, locators_file):
        snapshot_id = f"{feature}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if locators_file and Path(locators_file).exists():
            snapshot_path = SNAPSHOT_DIR / f"{snapshot_id}.py"
            shutil.copy(locators_file, snapshot_path)
            logger.info("snapshot_created", id=snapshot_id)
        return snapshot_id

    def _restore_snapshot(self, snapshot_id, locators_file):
        if not locators_file:
            return
        snapshot_path = SNAPSHOT_DIR / f"{snapshot_id}.py"
        if snapshot_path.exists():
            shutil.copy(snapshot_path, locators_file)
            logger.info("snapshot_restored", id=snapshot_id)

    def _update_locators_file(self, locators_file, element, old_locator, new_locator):
        try:
            content = Path(locators_file).read_text()
            updated = content.replace(f'"{old_locator}"', f'"{new_locator}"  # healed')
            updated = updated.replace(f"'{old_locator}'", f"'{new_locator}'  # healed")
            Path(locators_file).write_text(updated)
            logger.info("locator_file_updated", file=locators_file)
        except Exception as e:
            logger.error("locator_update_failed", error=str(e))


self_healer = SelfHealer()
