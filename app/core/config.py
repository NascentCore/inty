import sys

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

import yaml
from pydantic import AnyHttpUrl


@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    file: str = "inty.log"
    rotation: str = "100 MB"
    retention: str = "7 days"


@dataclass
class SecurityConfig:
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days


@dataclass
class DatabaseSettings:
    host: str
    port: int
    user: str
    password: str
    db: str
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
class AppConfig:
    name: str = "InTy"
    debug: bool = True
    debug_messages: bool = True
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: List[AnyHttpUrl] = None

    @dataclass
    class LimitsConfig:
        free_user_total_chat_message_limit: int = 1000
        subed_user_daily_chat_message_limit: int = 1000

    limits: LimitsConfig = field(default_factory=LimitsConfig)

    def __post_init__(self):
        if self.backend_cors_origins is None:
            self.backend_cors_origins = []


@dataclass
class EmbeddingConfig:
    base_url: str = "http://localhost:8001/v1"
    api_key: str = "sk-proj-1234567890"
    model: str = "DMetaSoul/Dmeta-embedding-zh-small"


@dataclass
class GoogleSearchConfig:
    api_key: str
    cse_id: str


@dataclass
class AgentConfig:
    model: str = "google/gemini-2.5-flash"
    base_url: str = "https://openrouter.ai/api/v1"
    api_key: str = "<fill-in-config.yaml>"
    temperature: float = 0.5
    max_tokens: int = 1000
    top_p: float = 1.0
    top_k: int = 50
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    enable_debug_logging: bool = False  # 是否启用调试日志记录功能
    vertex_image_model: str = "imagen-4.0-fast-generate-preview-06-06"


@dataclass
class GCSConfig:
    bucket: str
    credentials: str


@dataclass
class FirebaseConfig:
    service_account_path: str


@dataclass
class KeepTalkingConfig:
    enabled: bool = False  # 默认不启用keep_talking服务
    check_interval: int = 300  # 5分钟检查一次
    max_idle_time: int = 1800  # 30分钟没有回复则发送keep_talking消息
    max_keep_talking_messages: int = 3  # 最多发送3条keep_talking消息


@dataclass
class GooglePlayConfig:
    """Google Play配置"""

    service_account_key: str  # 服务账号密钥JSON字符串
    package_name: str  # 应用包名
    webhook_secret: Optional[str] = None  # Webhook密钥（可选）
    # 版本检查相关配置
    enable_version_check: bool = True  # 是否启用版本检查
    min_supported_version: int = 1  # 最低支持版本代码
    release_track: str = "production"  # 发布轨道：internal/closed/open/production
    fallback_tracks: List[str] = None  # 备用轨道列表

    def __post_init__(self):
        if self.fallback_tracks is None:
            self.fallback_tracks = ["production", "internal"]


@dataclass
class ElevenLabsConfig:
    """ElevenLabs语音生成配置"""

    api_key: str
    model: str = "eleven_multilingual_v2"
    voice_id: str = "JBFqnCBsd6RMkjVDRZzb"  # 默认语音ID
    output_format: str = "mp3_44100_128"
    enabled: bool = True
    max_text_length: int = 5000  # 最大文本长度限制


@dataclass
class SubscriptionPlan:
    """订阅计划配置"""

    id: str
    name: str
    description: Optional[str] = None
    plan_type: str = "MONTHLY"  # MONTHLY, QUARTERLY, YEARLY
    price: float = 0.0
    currency: str = "USD"
    google_play_product_id: str = ""
    discount_rate: float = 1.0  # 价格折扣率，范围0-1，1表示无折扣

    # 权益配置
    features: Dict[str, Any] = field(default_factory=dict)
    chat_limit_per_day: int = -1  # 每日聊天次数限制，-1为无限制
    agent_creation_limit: int = 6  # Agent创建数量限制
    background_generation_limit_per_day: int = 3  # 每日背景图生成次数限制，-1为无限制

    # 状态
    is_active: bool = True
    sort_order: int = 0


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
    google_search: GoogleSearchConfig
    firebase: FirebaseConfig
    keep_talking: KeepTalkingConfig
    google_play: GooglePlayConfig
    elevenlabs: ElevenLabsConfig
    subscription_plans: List[SubscriptionPlan] = field(default_factory=list)


def load_config(path: str) -> Config:
    config_path = Path(path)
    if not config_path.exists():
        print(f"config file {path} not found!")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Load subscription plans
    subscription_plans_data = data.get("subscription_plans", [])
    subscription_plans = [
        SubscriptionPlan(**plan_data) for plan_data in subscription_plans_data
    ]

    return Config(
        app=AppConfig(**data.get("app", {})),
        security=SecurityConfig(**data.get("security", {})),
        database=DatabaseSettings(**data.get("database", {})),
        google_oauth=GoogleOAuthConfig(**data.get("google_oauth", {})),
        verification=VerificationConfig(**data.get("verification", {})),
        logging=LoggingConfig(**data.get("logging", {})),
        embedding=EmbeddingConfig(**data.get("embedding", {})),
        agent=AgentConfig(**data.get("agent", {})),
        gcs=GCSConfig(**data.get("gcs", {})),
        google_search=GoogleSearchConfig(**data.get("google_search", {})),
        firebase=FirebaseConfig(**data.get("firebase", {})),
        keep_talking=KeepTalkingConfig(**data.get("keep_talking", {})),
        google_play=GooglePlayConfig(**data.get("google_play", {})),
        elevenlabs=ElevenLabsConfig(**data.get("elevenlabs", {})),
        subscription_plans=subscription_plans,
    )


global_config_loaded_from_config_yaml = load_config("config.yaml")
settings = global_config_loaded_from_config_yaml
