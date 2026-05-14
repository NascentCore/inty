"""Tests for loading OPENAI_API_KEY from YAML (harness demo)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from experimental.harness_seeding_demo.config_yaml_env import (
    apply_llm_env_from_config_yaml,
)


def test_apply_sets_openai_from_agent_api_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "c.yaml"
    cfg.write_text(
        yaml.dump({"agent": {"api_key": "sk-test-from-yaml"}}), encoding="utf-8"
    )

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    apply_llm_env_from_config_yaml(cfg)
    assert os.environ.get("OPENAI_API_KEY") == "sk-test-from-yaml"


def test_apply_skips_when_env_already_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "c.yaml"
    cfg.write_text(yaml.dump({"agent": {"api_key": "sk-yaml"}}), encoding="utf-8")

    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")

    apply_llm_env_from_config_yaml(cfg)
    assert os.environ.get("OPENAI_API_KEY") == "sk-env"


def test_apply_openai_api_key_top_level(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "c.yaml"
    cfg.write_text(yaml.dump({"openai_api_key": "sk-top"}), encoding="utf-8")

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    apply_llm_env_from_config_yaml(cfg)
    assert os.environ.get("OPENAI_API_KEY") == "sk-top"
