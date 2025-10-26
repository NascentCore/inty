import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

import yaml
from loguru import logger
from pydantic import AnyHttpUrl
#所有配置类的字段都应该有默认值。
# 这些默认值允许在没有实际配置文件的情况下使用它。
# 由于配置对象被全局使用，因此大多数代码都依赖于它，
#但实际上并没有使用配置值，因此默认值就可以了。
#
#所有默认值均应在 prduction 环境中使用。
# 配置。yaml。example 是开发环境的示例。

GEMINI_2_5_FLASH = "google/gemini-2.5-flash"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
API_V1_PREFIX = "/api/v1"


class Environment(str, Enum):
    """Environment enum for application deployment environments."""

    DEV = "dev"
    PROD = "prod"
    LOCAL = "local"
    UNSPECIFIED = "unspecified"


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
#配置配置后不能更改，否则现有的令牌将失效。
#这是因为令牌是使用此密钥加密的。
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
#应用程序可以承受更多的失败，并在调试模式下进行更多的日志记录。
    debug: bool = False
# DEPRECATED：不要使用。
    debug_messages: bool = True
# DEPRECATED：不要使用。
    api_v1_prefix: str = API_V1_PREFIX
    backend_cors_origins: List[AnyHttpUrl] = None
    version: str = "1.1.0"
    environment: Environment = Environment.DEV
    gcp_service_account_key: str = ".secrets/gcp-service-account-key.json"

    api_endpoints: APIEndpointsConfig = field(default_factory=APIEndpointsConfig)

    @dataclass
    class LimitsConfig:
#对于任何上传的图片，最大图片大小（以MB为单位）。
        max_image_size_mb: int = 4
# DEPRECATED：使用 free_user_image_gen_24h_limit 代替
        free_user_image_gen_daily_limit: int = 4
#仅用于测试目的，以便更轻松地与测试客户端集成。
        local_only_guest_user_image_gen_24h_limit: int = 0
        free_user_image_gen_24h_limit: int = 4
        subscribed_user_image_gen_24h_limit: int = 8
        free_user_agent_creation_24h_limit: int = 6
        subscribed_user_agent_creation_24h_limit: int = 12
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
# 需要 https:// 才能被开放路由器识别。
# 普通字符串将被开放路由器拒绝。
        return f"https://{self.name}-{self.environment.value}"


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
# DEPRECATED：不要使用。
    enable_debug_logging: bool = False  # 是否启用调试日志记录功能
    vertex_image_model: str = "imagen-4.0-fast-generate-001"
    force_default_prompts: bool = False  # 强制使用默认提示词，忽略Agent自定义提示词


@dataclass
class GCSConfig:
    bucket: str
# DEPRECATED: 保留作为兼容；被应用程序。gcp_service_account_key 取代
# 删除配置环境中的配置文件使用，然后删除该代码。
    credentials: str = "<deprecated-do-not-use>"


@dataclass
class FirebaseConfig:
    service_account_path: str


@dataclass
class GooglePlayConfig:
    """Google Play配置"""
# DEPRECATED: 保留作为兼容；被应用程序。gcp_service_account_key 取代
# 删除配置环境中的配置文件使用，然后删除该代码。
    service_account_key: str = "inty-backend-key.json"
    package_name: str = "com.ai.intellimate"
    webhook_secret: Optional[str] = None  # Webhook密钥（可选）
# 版本检查相关配置
    enable_version_check: bool = True  # 是否启用版本检查
    min_supported_version: int = 1  # 最低支持版本代码
# DEPRECATED: 芭使用过。
# 删除配置环境中的配置文件使用，然后删除该代码。
    release_track: str = "production"  # 发布轨道：internal/closed/open/production
# DEPRECATED: 芭使用过。
# 删除配置环境中的配置文件使用，然后删除该代码。
    fallback_tracks: List[str] = None  # 备用轨道列表
#添加版本检查配置
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

    print(f"[CONFIG] Loading config from: {config_path.absolute()}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
# 处理有限制的唤醒应用程序配置
    app_data = data.get("app", {})
    if "limits" in app_data and isinstance(app_data["limits"], dict):
        app_data["limits"] = AppConfig.LimitsConfig(**app_data["limits"])
# 将环境字符串转换为环境枚举 if present
    if "environment" in app_data and isinstance(app_data["environment"], str):
        app_data["environment"] = Environment(app_data["environment"])

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
    """Validate config values with auto-correction"""
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
# 验证并自动修改限制配置
    limits = config.app.limits
#规则1:游客语音生成次数对应的聊天次数，否则与聊天次数相同
    if limits.guest_user_voice_24h_limit != limits.guest_user_chat_24h_limit:
        logger.warning(
            f"Config issue: guest_user_voice_24h_limit ({limits.guest_user_voice_24h_limit}) "
            f"!= guest_user_chat_24h_limit ({limits.guest_user_chat_24h_limit}). "
            f"Auto-correcting to {limits.guest_user_chat_24h_limit}"
        )
        limits.guest_user_voice_24h_limit = limits.guest_user_chat_24h_limit
#规则2:登录用户语音生成次数应等于聊天次数，否则以聊天次数为准
    if limits.free_user_voice_24h_limit != limits.free_user_chat_24h_limit:
        logger.warning(
            f"Config issue: free_user_voice_24h_limit ({limits.free_user_voice_24h_limit}) "
            f"!= free_user_chat_24h_limit ({limits.free_user_chat_24h_limit}). "
            f"Auto-correcting to {limits.free_user_chat_24h_limit}"
        )
        limits.free_user_voice_24h_limit = limits.free_user_chat_24h_limit
# 规则3: 游客聊天次数应<=登录用户，否则使用默认值
    if limits.guest_user_chat_24h_limit > limits.free_user_chat_24h_limit:
        default_guest = 10
        default_free = 100
        logger.warning(
            f"Config issue: guest_user_chat_24h_limit ({limits.guest_user_chat_24h_limit}) "
            f"> free_user_chat_24h_limit ({limits.free_user_chat_24h_limit}). "
            f"Auto-correcting to defaults: guest={default_guest}, free={default_free}"
        )
        limits.guest_user_chat_24h_limit = default_guest
        limits.free_user_chat_24h_limit = default_free
# 同步修改语音限制
        limits.guest_user_voice_24h_limit = default_guest
        limits.free_user_voice_24h_limit = default_free

    if (
        config.app.environment != Environment.LOCAL
        and limits.local_only_guest_user_image_gen_24h_limit > 0
    ):
        raise ValueError(
            "local_only_guest_user_image_gen_24h_limit is only allowed in local environment"
        )


global_config_loaded_from_config_yaml = load_config("config.yaml")
print(f"[CONFIG] Database URL: {global_config_loaded_from_config_yaml.database.url}")
_validate_config(global_config_loaded_from_config_yaml)
#设置LangSmith环境变量用于支持溯源，因为其只支持从环境变量读取设置，而不是依赖注入。
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
