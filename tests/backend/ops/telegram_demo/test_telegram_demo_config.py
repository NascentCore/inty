"""Tests for agent.channels.telegram config loading."""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.utils.config import load_config, resolved_telegram_bot_token


def test_load_config_telegram_channels_nested_token() -> None:
    from tests.app.utils.test_config import _minimal_yaml_for_load_config

    yaml_text = _minimal_yaml_for_load_config("").replace(
        "agent:\n",
        "\n".join(
            [
                "agent:",
                "  channels:",
                "    telegram:",
                "      bot_token: nested-token",
                "",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))
    assert cfg.agent.channels.telegram.bot_token == "nested-token"
    assert resolved_telegram_bot_token(cfg.agent) == "nested-token"


def test_load_config_telegram_harness_memory_bootstrap_type() -> None:
    from tests.app.utils.test_config import (
        _minimal_yaml_for_load_config_harness,
    )

    yaml_text = _minimal_yaml_for_load_config_harness(
        "    memory_bootstrap_type: USER_INTERACTIVE\n",
    ).replace(
        "agent:\n",
        "\n".join(
            [
                "agent:",
                "  channels:",
                "    telegram:",
                "      bot_token: nested-token",
                "",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))
    assert (
        cfg.agent.companion_harness.memory_bootstrap_type == "USER_INTERACTIVE"
    )
