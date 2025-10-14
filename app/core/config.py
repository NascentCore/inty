import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml
from loguru import logger
from pydantic import AnyHttpUrl

# All config classes' fields should have default values.
# These default value allow this to be used without an actual config file.
# Since config object is used as a global singleton, most code depends on it,
# but does not actually use the config values, so a default value is OK.
#
# All default values should be assumed to be used in production environment.
# config.yaml.example is a sample for development environment.

GEMINI_2_5_FLASH = "google/gemini-2.5-flash"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
API_V1_PREFIX = "/api/v1"
API_V2_PREFIX = "/api/v2"


@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS zz} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    file: str = "inty.log"
    rotation: str = "100 MB"
    retention: str = "7 days"


@dataclass
class SecurityConfig:
    # This config cannot be changed after it's deployed, otherwise the existing tokens will be invalid.
    # This is because the token is encrypted using this secret key.
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days


@dataclass
class DatabaseSettings:
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = "sxwl666!"
    db: str = "inty"
    pool_size: int = 50
    max_overflow: int = 20
    pool_timeout: int = 10
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    connect_timeout: int = 5
    command_timeout: int = 30

    @property
    def url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def async_url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


@dataclass
class GoogleOAuthConfig:
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None


@dataclass
class VerificationConfig:
    code_expire_minutes: int = 5


@dataclass
class APIEndpointsConfig:
    disable_api_v1_chat_completions: bool = False


@dataclass
class AppConfig:
    name: str = "inty-backend"
    # The app tolerates more failures, and does more logging in the debug mode.
    debug: bool = False
    # DEPRECATED: Do not use.
    debug_messages: bool = True
    # DEPRECATED: Do not use.
    api_v1_prefix: str = API_V1_PREFIX
    backend_cors_origins: List[AnyHttpUrl] = None
    version: str = "1.1.0"
    environment: str = "dev"
    gcp_service_account_key: str = ".secrets/gcp-service-account-key.json"

    @dataclass
    class LimitsConfig:
        # Maximal image size in MB, for any uploaded images.
        max_image_size_mb: int = 4
        free_user_image_gen_daily_limit: int = 4
        free_user_chat_total_limit: int = 100
        free_user_chat_24h_limit: int = 100
        guest_user_chat_24h_limit: int = 10
        free_user_voice_24h_limit: int = 100
        guest_user_voice_24h_limit: int = 10
        subscribed_user_voice_24h_limit: int = 100
        image_compression_threshold_size_kb: int = 500

    limits: LimitsConfig = None

    def __post_init__(self):
        if self.limits is None:
            self.limits = self.LimitsConfig()

    @property
    def name_for_openrouter(self) -> str:
        # https:// is required to make it recognized by open router.
        # Normal string will be rejected by open router.
        return f"https://{self.name}-{self.environment}"


@dataclass
class EmbeddingConfig:
    base_url: str = "http://localhost:8001/v1"
    api_key: str = "sk-proj-1234567890"
    model: str = "DMetaSoul/Dmeta-embedding-zh-small"


@dataclass
class AgentConfig:
    api_key: str
    langchain_api_key: str
    model: str = GEMINI_2_5_FLASH
    base_url: str = OPENROUTER_BASE_URL
    temperature: float = 0.5
    max_tokens: int = 1000
    top_p: float = 1.0
    top_k: int = 50
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    # DEPRECATED: Do not use.
    enable_debug_logging: bool = False  # 是否启用调试日志记录功能
    vertex_image_model: str = "imagen-4.0-fast-generate-001"
    force_default_prompts: bool = False  # 强制使用默认提示词，忽略Agent自定义提示词


@dataclass
class GCSConfig:
    bucket: str
    # DEPRECATED: 保留作为兼容；被 app.gcp_service_account_key 取代
    # 删除部署环境中的配置文件使用，然后删除这个代码。
    credentials: str = "<deprecated-do-not-use>"


@dataclass
class FirebaseConfig:
    service_account_path: str


@dataclass
class GooglePlayConfig:
    """Google Play配置"""

    # DEPRECATED: 保留作为兼容；被 app.gcp_service_account_key 取代
    # 删除部署环境中的配置文件使用，然后删除这个代码。
    service_account_key: str = "inty-backend-key.json"
    package_name: str = "com.ai.intellimate"
    webhook_secret: Optional[str] = None  # Webhook密钥（可选）
    # 版本检查相关配置
    enable_version_check: bool = True  # 是否启用版本检查
    min_supported_version: int = 1  # 最低支持版本代码
    # DEPRECATED: 未被使用过。
    # 删除部署环境中的配置文件使用，然后删除这个代码。
    release_track: str = "production"  # 发布轨道：internal/closed/open/production
    # DEPRECATED: 未被使用过。
    # 删除部署环境中的配置文件使用，然后删除这个代码。
    fallback_tracks: List[str] = None  # 备用轨道列表
    # 新增版本检查配置
    max_minor_version_gap: int = 10  # Minor版本号最大差距，超过则强制更新

    def __post_init__(self):
        if self.fallback_tracks is None:
            self.fallback_tracks = ["production", "internal"]


@dataclass
class CloudflareConfig:
    """Cloudflare CDN代理配置"""

    domain: str = ""  # Cloudflare代理的域名
    enabled: bool = False  # 是否启用Cloudflare CDN代理
    fallback_to_original: bool = True  # 转换失败时是否回退到原始URL


@dataclass
class ElevenLabsConfig:
    """ElevenLabs语音生成配置"""

    api_key: str
    model: str = "eleven_multilingual_v2"
    voice_id: str = "JBFqnCBsd6RMkjVDRZzb"  # 默认语音ID
    output_format: str = "mp3_44100_128"
    enabled: bool = True
    max_text_length: int = 5000  # 最大文本长度限制
    ssl_verify: bool = True  # SSL证书验证开关


@dataclass
class Config:
    app: AppConfig
    security: SecurityConfig
    database: DatabaseSettings
    google_oauth: GoogleOAuthConfig
    verification: VerificationConfig
    logging: LoggingConfig
    embedding: EmbeddingConfig
    agent: AgentConfig
    gcs: GCSConfig
    firebase: FirebaseConfig
    google_play: GooglePlayConfig
    elevenlabs: ElevenLabsConfig
    cloudflare: CloudflareConfig


def load_config(path: str) -> Config:
    config_path = Path(path)
    if not config_path.exists():
        print(f"config file {path} not found!")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Handle nested app config with limits
    app_data = data.get("app", {})
    if "limits" in app_data and isinstance(app_data["limits"], dict):
        app_data["limits"] = AppConfig.LimitsConfig(**app_data["limits"])

    return Config(
        app=AppConfig(**app_data),
        security=SecurityConfig(**data.get("security", {})),
        database=DatabaseSettings(**data.get("database", {})),
        google_oauth=GoogleOAuthConfig(**data.get("google_oauth", {})),
        verification=VerificationConfig(**data.get("verification", {})),
        logging=LoggingConfig(**data.get("logging", {})),
        embedding=EmbeddingConfig(**data.get("embedding", {})),
        agent=AgentConfig(**data.get("agent", {})),
        gcs=GCSConfig(**data.get("gcs", {})),
        firebase=FirebaseConfig(**data.get("firebase", {})),
        google_play=GooglePlayConfig(**data.get("google_play", {})),
        elevenlabs=ElevenLabsConfig(**data.get("elevenlabs", {})),
        cloudflare=CloudflareConfig(**data.get("cloudflare", {})),
    )


def _validate_config(config: Config):
    """Validate config values"""
    if not config.app.gcp_service_account_key:
        raise ValueError("app.gcp_service_account_key is required")
    if not config.agent.api_key:
        raise ValueError("agent.api_key is required")
    if not config.agent.langchain_api_key:
        raise ValueError("agent.langchain_api_key is required")
    if not config.gcs.bucket:
        raise ValueError("gcs.bucket is required")
    if not config.firebase.service_account_path:
        raise ValueError("firebase.service_account_path is required")
    if not config.elevenlabs.api_key:
        raise ValueError("elevenlabs.api_key is required")


global_config_loaded_from_config_yaml = load_config("config.yaml")
_validate_config(global_config_loaded_from_config_yaml)


# 设置 LangSmith 环境变量用于支持 tracing，因为其只支持从环境变量读取设置，而非依赖注入。
os.environ["LANGSMITH_TRACING_V2"] = "true"
os.environ["LANGSMITH_PROJECT"] = (
    f"{global_config_loaded_from_config_yaml.app.name}-{global_config_loaded_from_config_yaml.app.environment}"
)
os.environ["LANGCHAIN_API_KEY"] = (
    global_config_loaded_from_config_yaml.agent.langchain_api_key
)
logger.debug(f"Setting LangSmith environment variables for project: ")
logger.debug(f"LANGSMITH_TRACING_V2: {os.getenv('LANGSMITH_TRACING_V2')}")
logger.debug(f"LANGSMITH_PROJECT: {os.getenv('LANGSMITH_PROJECT')}")
logger.debug(f"LANGCHAIN_API_KEY: {os.getenv('LANGCHAIN_API_KEY')}")
