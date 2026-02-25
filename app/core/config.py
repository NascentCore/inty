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
    SentryConfig,
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


# 设置 LangSmith 环境变量用于支持 tracing，因为其只支持从环境变量读取设置，而非依赖注入。
os.environ["LANGSMITH_TRACING_V2"] = "true"
os.environ["LANGSMITH_PROJECT"] = (
    f"{global_config_loaded_from_config_yaml.app.name}-{global_config_loaded_from_config_yaml.app.environment.value}"
)
os.environ["LANGCHAIN_API_KEY"] = (
    global_config_loaded_from_config_yaml.agent.langchain_api_key
)
logger.debug(f"Setting LangSmith environment variables for project: ")
logger.debug(f"LANGSMITH_TRACING_V2: {os.getenv('LANGSMITH_TRACING_V2')}")
logger.debug(f"LANGSMITH_PROJECT: {os.getenv('LANGSMITH_PROJECT')}")
logger.debug(f"LANGCHAIN_API_KEY: {os.getenv('LANGCHAIN_API_KEY')}")

os.environ["FAL_KEY"] = global_config_loaded_from_config_yaml.fal.api_key
logger.debug(f"Setting FAL_KEY environment variable: {os.getenv('FAL_KEY')}")
