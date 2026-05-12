"""Load Inty YAML config at process import time.

Path: ``INTY_CONFIG_YAML`` when set, otherwise ``config.yaml`` in the current working directory.
"""

import getpass
import os

from loguru import logger

from app.utils.config import (
    # TODO: 删除这些间接倒入，在调用处替换为直接倒入 app.utils.*
    APIEndpointsConfig,
    AgentConfig,
    AppConfig,
    CloudflareConfig,
    Config,
    DatabaseSettings,
    ElevenLabsConfig,
    EmbeddingConfig,
    Environment,
    FeaturesConfig,
    FirebaseConfig,
    GCSConfig,
    GEMINI_2_5_FLASH,
    GEMINI_2_5_FLASH_LITE,
    GeminiLiveConfig,
    GoogleOAuthConfig,
    GooglePlayConfig,
    LoggingConfig,
    MemoryExtractionConfig,
    PushNotificationConfig,
    SecurityConfig,
    UserAnalyticsReportConfig,
    VerificationConfig,
    # End of 间接倒入
    _validate_config,
    load_config,
)

_CONFIG_PATH = (
    os.environ.get("INTY_CONFIG_YAML") or "config.yaml"
).strip() or "config.yaml"
if not os.path.exists(_CONFIG_PATH):
    raise FileNotFoundError(
        f"{_CONFIG_PATH} 不存在，倒入本模块前请先创建配置文件或设置 INTY_CONFIG_YAML"
    )
global_config_loaded_from_config_yaml = load_config(_CONFIG_PATH)
logger.debug(
    "[CONFIG] path={} database URL: {}",
    _CONFIG_PATH,
    global_config_loaded_from_config_yaml.database.url,
)
_validate_config(global_config_loaded_from_config_yaml)


def _langsmith_tracing_v2_enabled(config: Config) -> bool:
    """LangSmith tracing 开关：config.yaml 中 agent.langsmith_tracing_enabled（默认 true）。"""
    return bool(getattr(config.agent, "langsmith_tracing_enabled", True))


def _langsmith_local_username_slug() -> str:
    user = (os.getenv("USER") or os.getenv("USERNAME") or "").strip()
    if not user:
        try:
            user = getpass.getuser()
        except Exception:
            user = ""
    if not user:
        user = "unknown"
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in user)
    parts = [p for p in safe.split("-") if p]
    slug = "-".join(parts)
    return slug or "unknown"


def set_langsmith_environment_variables(config: Config) -> None:
    # LangSmith SDK 仍读取进程环境变量；此处根据 YAML 写入 LANGSMITH_TRACING_V2 等。
    langsmith_project = f"{config.app.name}-{config.app.environment.value}"
    if config.app.environment == Environment.LOCAL:
        langsmith_project = f"{langsmith_project}-{_langsmith_local_username_slug()}"
    tracing_enabled = _langsmith_tracing_v2_enabled(config)
    os.environ["LANGSMITH_TRACING_V2"] = "true" if tracing_enabled else "false"
    os.environ["LANGSMITH_PROJECT"] = langsmith_project
    os.environ["LANGCHAIN_API_KEY"] = config.agent.langchain_api_key
    logger.debug(
        "Setting LangSmith environment variables (before init_logger; may only hit default sink)"
    )
    logger.debug(f"LANGSMITH_TRACING_V2: {os.getenv('LANGSMITH_TRACING_V2')}")
    logger.debug(f"LANGSMITH_PROJECT: {os.getenv('LANGSMITH_PROJECT')}")
    has_ls_key = bool((config.agent.langchain_api_key or "").strip())
    logger.debug(
        f"LANGCHAIN_API_KEY: {'set' if has_ls_key else 'empty'} (value not logged)"
    )


set_langsmith_environment_variables(global_config_loaded_from_config_yaml)

os.environ["FAL_KEY"] = global_config_loaded_from_config_yaml.fal.api_key
has_fal_key = bool((global_config_loaded_from_config_yaml.fal.api_key or "").strip())
logger.debug(
    f"fal_client 读取环境变量：FAL_KEY {'set' if has_fal_key else 'empty'} (value not logged)"
)
