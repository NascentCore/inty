import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"


@dataclass
class ServerSettings:
    host: str = "0.0.0.0"
    port: int = 9001
    stun_server: str = "stun:stun.l.google.com:19302"
    log_level: str = "info"


@dataclass
class GeminiConfig:
    api_key: Optional[str] = None
    model: str = "gemini-live-2.5-flash-preview-native-audio-09-2025"
    voice_name: str = "Zephyr"
    send_sample_rate: int = 16000
    receive_sample_rate: int = 24000


@dataclass
class Config:
    server: ServerSettings = field(default_factory=ServerSettings)
    gemini: GeminiConfig = field(default_factory=GeminiConfig)


def load_config(path: Optional[str] = None) -> Config:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        # allow running with env var GOOGLE_API_KEY only
        return Config()

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    server_data = data.get("server", {})
    gemini_data = data.get("gemini", {})
    if isinstance(gemini_data.get("api_key"), str):
        # Expand env vars like ${GOOGLE_API_KEY}
        gemini_data["api_key"] = (
            os.path.expandvars(gemini_data["api_key"]) or None
        )

    cfg = Config(
        server=ServerSettings(**server_data), gemini=GeminiConfig(**gemini_data)
    )

    # Export Google API key to env for google-genai
    if cfg.gemini.api_key and not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = cfg.gemini.api_key

    return cfg
