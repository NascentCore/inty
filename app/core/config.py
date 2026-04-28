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

DEFAULT_CONFIG_PATH = "config.yaml"
if not os.path.exists(DEFAULT_CONFIG_PATH):
    raise FileNotFoundError(
        f"{DEFAULT_CONFIG_PATH} 不存在，倒入本模块前请先创建配置文件"
    )
global_config_loaded_from_config_yaml = load_config(DEFAULT_CONFIG_PATH)
logger.debug(
    f"[CONFIG] Database URL: {global_config_loaded_from_config_yaml.database.url}"
)
_validate_config(global_config_loaded_from_config_yaml)


def _langsmith_tracing_v2_enabled() -> bool:
    """
    Sole switch for LangSmith tracing: enable only when LANGSMITH_TRACING_V2 is a
    truthy token. Unset, empty, false-like, or unrecognized values all mean off.
    """
    raw = os.environ.get("LANGSMITH_TRACING_V2")
    if raw is None:
        return False
    lo = raw.strip().lower()
    return lo in ("1", "true", "yes", "on")


def set_langsmith_environment_variables(config: Config) -> None:
    # LangSmith 仅支持通过环境变量控制 tracing，不支持依赖注入。
    langsmith_project = f"{config.app.name}-{config.app.environment.value}"
    tracing_enabled = _langsmith_tracing_v2_enabled()
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
