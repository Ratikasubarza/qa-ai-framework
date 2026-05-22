from pathlib import Path

import pytest

from agents.code_generator_agent import CodeGeneratorAgent


def test_parse_files_normalizes_conftest_into_feature_steps():
    agent = CodeGeneratorAgent()
    raw = "# === FILE: conftest.py ===\nimport pytest\n"

    files = agent._parse_files(raw, "login")

    assert "features/login/steps/conftest.py" in files


def test_save_files_allows_only_feature_scoped_output(monkeypatch, tmp_path):
    agent = CodeGeneratorAgent()
    safe_root = (tmp_path / "features").resolve()
    feature_root = (safe_root / "login").resolve()
    (feature_root / "steps").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(agent, "_SAFE_OUTPUT_ROOT", safe_root)
    monkeypatch.setattr("core.code_security.validate_generated_code", lambda content, file_path: None)

    good_file = feature_root / "steps" / "generated_test.py"
    saved = agent._save_files(
        {str(good_file): "def test_generated():\n    assert True\n"},
        "login",
    )

    assert str(good_file) in saved.values()
    assert good_file.exists()


def test_save_files_blocks_prefix_escape_path(monkeypatch, tmp_path):
    agent = CodeGeneratorAgent()
    safe_root = (tmp_path / "features").resolve()
    (safe_root / "login" / "steps").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(agent, "_SAFE_OUTPUT_ROOT", safe_root)
    monkeypatch.setattr("core.code_security.validate_generated_code", lambda content, file_path: None)

    # Prefix lookalike path that used to pass string-prefix checks.
    escaped = (tmp_path / "features_login" / "steps" / "evil.py").resolve()

    with pytest.raises(ValueError):
        agent._save_files(
            {str(escaped): "def test_escape():\n    assert True\n"},
            "login",
        )
