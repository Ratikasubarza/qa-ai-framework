"""
Prompt Manager — loads versioned prompts from registry.
Prompts are treated as code: versioned, logged, traceable.
"""
import yaml
import structlog
from pathlib import Path
from typing import Optional

logger = structlog.get_logger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent
PROMPTS_DIR   = _PROJECT_ROOT / "prompts"
REGISTRY_PATH = PROMPTS_DIR / "prompt_registry.yaml"


class PromptTemplate:
    def __init__(self, name: str, version: str, template: str, model_tier: str):
        self.name       = name
        self.version    = version
        self.template   = template
        self.model_tier = model_tier

    def format(self, **kwargs) -> str:
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(
                f"Prompt '{self.name}' v{self.version} "
                f"missing required variable: {e}"
            )


class PromptManager:
    def __init__(self):
        self._registry: dict = {}
        self._templates: dict[str, PromptTemplate] = {}
        self._load_registry()

    def _load_registry(self):
        with open(REGISTRY_PATH) as f:
            self._registry = yaml.safe_load(f) or {}
        for name, meta in self._registry.get("prompts", {}).items():
            if meta.get("archived", False):
                logger.info("prompt_archived_skipped", name=name, version=meta.get("version"))
                continue
            self._load_prompt(name, meta)
        logger.info("prompts_loaded", count=len(self._templates))

    def _load_prompt(self, name: str, meta: dict):
        template_path = _PROJECT_ROOT / meta["template_ref"]
        if not template_path.exists():
            logger.warning("prompt_file_missing", name=name, path=str(template_path))
            return
        with open(template_path) as f:
            template_text = f.read()
        self._templates[name] = PromptTemplate(
            name=name,
            version=meta["version"],
            template=template_text,
            model_tier=meta.get("model_tier", "standard"),
        )

    def get(self, name: str) -> PromptTemplate:
        if name not in self._templates:
            raise KeyError(
                f"Prompt '{name}' not found in registry. "
                f"Available: {list(self._templates.keys())}"
            )
        return self._templates[name]

    def reload(self):
        """Hot-reload prompts without restarting the process."""
        self._templates.clear()
        self._load_registry()
        logger.info("prompts_reloaded")


prompt_manager = PromptManager()
