from pathlib import Path

import pytest
import yaml

from core.prompt_manager import PromptManager


def test_prompt_registry_marks_test_case_v1_as_archived():
    registry_path = Path("prompts/prompt_registry.yaml")
    data = yaml.safe_load(registry_path.read_text(encoding="utf-8"))

    prompt_meta = data["prompts"]["test_case_gen_v1"]
    assert prompt_meta["archived"] is True


def test_prompt_manager_loads_test_case_v2_as_only_runtime_path():
    manager = PromptManager()

    template = manager.get("test_case_gen")
    assert template.version == "2.0.0"

    with pytest.raises(KeyError):
        manager.get("test_case_gen_v1")
