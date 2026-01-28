import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

import yaml
from loguru import logger
from pydantic import AnyHttpUrl

# 所有配置项必须有默认值，防止出现校验失败。
# 这些默认值允许在没有实际配置文件的情况下使用。
# 因为 config 对象被用作全局单例，大部分代码依赖它，但并不实际使用配置值，所以默认值是可以的。
# 但是所有默认值都应该假设在生产环境中使用。
#
# 废弃某个配置项时的步骤：
# 1. 删除该配置项在 Python 代码中的使用，部署、发布验证一切正常。
# 2. 删除该配置项在 devops/config.yaml.<env> 中的使用，部署、发布验证一切正常。
# 3. 【如有必要】删除该配置项在 app 客户端相关的使用，部署、发布验证一切正常。

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# 3X of lite: $0.30	$0.30	$0.030	$0.030	$0.15	$0.15
GEMINI_2_5_FLASH = "google/gemini-2.5-flash"
# $0.1	$0.1	$0.010	$0.010	$0.05	$0.05
GEMINI_2_5_FLASH_LITE = "google/gemini-2.5-flash-lite"

# 3X of fast: $0.06 per image
VERTEX_AI_IMAGEN_4_ULTRA = "imagen-4.0-ultra-generate-001"
# 0.02 per image, 这个可以调整为更弱的模型
VERTEX_AI_IMAGEN_4_FAST = "imagen-4.0-fast-generate-001"


class Environment(str, Enum):
    """指明该后端实例运行的环境，对应不同的配置文件，位于 devops/config.yaml.<environment>。"""

    # 部署在测试环境中，用于测试。
    # 使用本地数据库，依赖的外部服务均为假的本地实现（位于 app/external_services/fakes/），
    # 只能返回固定结果，需要手动修改来改变其返回值。
    TEST = "test"

    # 部署在本地与 app 同在同一个局域网内，用于本地开发、测试。
    # 使用本地数据库，依赖的外部服务（GCS、Firebase、ElevenLabs等）仍然是真实的。
    LOCAL = "local"

    # 部署在共享的开发环境中，用于开发、测试。
    # 使用共享的开发数据库，同时依赖的外部服务如 GCS、Firebase、ElevenLabs 与生产环境一致。
    DEV = "dev"

    # 部署在生产环境中，用于支持公开用户在互联网上访问。
    PROD = "prod"


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
    # 使用虚假的 Google 登录接口，用于测试，设为 True 时可以在 auth.py 中直接定义返回值来支持 app 前端测试。
    use_dummy_api_v1_auth_google_login: bool = False
    use_dummy_api_v1_character_themes_get: bool = False
    use_dummy_api_v1_character_themes_id_get: bool = False


@dataclass
class AppConfig:
    name: str = "inty-backend"
    # The app tolerates more failures, and does more logging in the debug mode.
    debug: bool = False
    # DEPRECATED: Do not use.
    debug_messages: bool = True
    # Use JSON format for request/response logging. Default is True (JSON format).
    use_json_log_format: bool = True
    backend_cors_origins: List[AnyHttpUrl] = None
    version: str = "1.1.0"
    environment: Environment = Environment.DEV
    gcp_service_account_key: str = ".secrets/gcp-service-account-key.json"
    api_v1_prefix: str = "/api/v1"

    api_endpoints: APIEndpointsConfig = field(default_factory=APIEndpointsConfig)

    @dataclass
    class LimitsConfig:
        # Maximal image size in MB, for any uploaded images.
        max_image_size_mb: int = 4
        # DEPRECATED: Use free_user_image_gen_24h_limit instead
        free_user_image_gen_daily_limit: int = 4
        # Only used for testing purpose to allow easier integration with test client.
        test_only_guest_user_image_gen_24h_limit: int = 0
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
        # https:// is required to make it recognized by open router.
        # Normal string will be rejected by open router.
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
    # Free users (non-superuser) use this model by default to reduce cost.
    free_user_chat_model: str = GEMINI_2_5_FLASH_LITE
    # Subscribed users and superusers use this model by default.
    sub_user_chat_model: str = GEMINI_2_5_FLASH
    # Note: Model selection is handled by app.core.model_selection.select_chat_model(),
    # which automatically chooses between free_user_chat_model and sub_user_chat_model
    # based on user subscription status and superuser privileges.
    # 下面的代码文件不需要检测订阅状态，因为 evaluation 是做评测，不部面向用户
    # - app/services/evaluation_service.py (updated to use select_chat_model)
    base_url: str = OPENROUTER_BASE_URL
    temperature: float = 0.5
    max_tokens: int = 1000
    top_p: float = 1.0
    top_k: int = 50
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    # DEPRECATED: Do not use.
    enable_debug_logging: bool = False  # 是否启用调试日志记录功能
    vertex_image_model: str = VERTEX_AI_IMAGEN_4_FAST
    free_user_text_to_image_model: str = "fal-ai/z-image/turbo"
    sub_user_text_to_image_model: str = VERTEX_AI_IMAGEN_4_ULTRA
    force_default_prompts: bool = False  # 强制使用默认提示词，忽略Agent自定义提示词
    enable_christmas_prompt: bool = False  # 是否启用圣诞节季节性提示词
    # 图片生成配置
    image_generation_default_history_count: int = 10
    # 消息生图（chat image）模型配置
    # "gemini" 表示使用 Gemini 2.5 Flash Image，其他值为 fal.ai 模型名
    free_user_chat_image_model: str = "gemini"
    sub_user_chat_image_model: str = "gemini"
    # 视频生成配置
    veo3_model: str = "veo-3.0-fast-generate-preview"  # Veo3 模型名称
    # 动图配置
    animated_image_max_size_mb: int = 10  # 动图文件大小限制（MB）
    animated_image_fps: int = 15  # 动图帧率
    animated_image_max_width: int = 720  # 动图最大宽度
    preferred_animated_format: str = "avif"  # 首选格式：avif 或 gif


@dataclass
class GCSConfig:
    bucket: str = "inty-storage"
    # DEPRECATED: 保留作为兼容；被 app.gcp_service_account_key 取代
    # 删除部署环境中的配置文件使用，然后删除这个代码。
    credentials: str = "<deprecated-do-not-use>"
    # 如果为 True，则使用假GCS客户端；在本地存储文件，不使用 GCS 服务。用于测试。
    use_fake_gcs: bool = False
    fake_gcs_base_dir: str = "/tmp/inty_fake_gcs"


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
    # DEPRECATED: 未被使用过。使用 force_update_version_code_gap 替代，可以取得类似的效果。
    min_supported_version: int = 1  # 最低支持版本代码
    # DEPRECATED: 未被使用过。
    # 删除部署环境中的配置文件使用，然后删除这个代码。
    release_track: str = "production"  # 发布轨道：internal/closed/open/production
    # DEPRECATED: 未被使用过。
    # 删除部署环境中的配置文件使用，然后删除这个代码。
    fallback_tracks: List[str] = None  # 备用轨道列表
    # DEPRECATED: 不检查 version name，只检查 version code，这样使用简单的线性递增逻辑，很容易理解。
    max_minor_version_gap: int = 10  # Minor版本号最大差距，超过则强制更新
    # 当前生产环境版本代码（覆盖值）：
    # - 设置为正数时，版本检查直接使用此值，不调用 Google Play API（避免 edits.insert 配额消耗）
    # - 设置为 0 或未配置时，通过 Google Play API 动态获取版本信息
    current_version_code: int = 2986  # 当前 Google Play 生产环境的版本代码
    # 版本代码差距阈值配置；线性递增的多个阈值，超过某个阈值意味着之前超越的阈值的动作都会在 app 端执行。
    # 比如，触发 popup_reminder_version_code_gap 动作，意味着 settings reminder 与 popup reminder 都会在 app 端执行。
    force_update_version_code_gap: int = 1000  # 版本代码差距超过此值则强制更新
    popup_reminder_version_code_gap: int = 200  # 版本代码差距在此值以上则显示弹窗提醒
    settings_reminder_version_code_gap: int = 1  # 版本代码差距在此值以上则显示设置提醒


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
class SentryConfig:
    """Sentry 错误监控配置"""

    # Sentry DSN，例如: "https://examplePublicKey@o0.ingest.sentry.io/0"
    dsn: str = ""
    # 是否启用 Sentry
    enabled: bool = True
    # Traces 采样率，0.0-1.0，用于性能监控
    # 1.0 表示 100% 采样，0.1 表示 10% 采样
    traces_sample_rate: float = 1.0


@dataclass
class MemoryExtractionConfig:
    """记忆抽取定时任务配置；api_key/base_url 复用 agent。"""

    enabled: bool = True
    model: str = ""  # 为空时复用 agent.model
    cron_hour: int = 3  # UTC 小时，每日执行
    trigger_new_user_messages: int = 30  # 新用户总消息数阈值
    trigger_incremental_messages: int = 30  # 已提取用户自上次后新增消息数阈值


@dataclass
class PushNotificationConfig:
    """推送通知服务配置"""

    enabled: bool = True  # 是否启用推送服务
    batch_size: int = 50  # 每批处理的聊天数量
    max_retries: int = 3  # 最大重试次数
    max_concurrent_workers: int = 50  # 最大并发 worker 数
    workers_per_user_ratio: int = (
        10  # 每 N 个用户分配 1 个 worker（如 10 表示每 10 个用户 1 个 worker）
    )
    stages: dict = (
        None  # 推送阶段策略配置（10min, 30min, 2h, 24h, 48h），有聊天记录和无聊天记录用户共用
    )

    def __post_init__(self):
        if self.stages is None:
            self.stages = {
                "10min": {"count": 0, "minutes": 10},
                "30min": {"count": 1, "minutes": 30},
                "2h": {"count": 2, "minutes": 120},
                "24h": {"count": 3, "hours": 24},
                "48h": {"count": 4, "hours": 48},
            }


@dataclass
class FalConfig:
    """fal.ai 生图服务配置"""

    api_key: str = ""  # fal.ai API key


@dataclass
class GeminiLiveConfig:
    """Gemini Live API 实时语音通话配置
    使用 Vertex AI 模式，复用 app.gcp_service_account_key 进行认证
    """

    enabled: bool = False  # 是否启用实时语音通话功能
    project_id: str = "inty-backend"  # GCP 项目 ID
    location: str = "us-central1"  # Vertex AI 区域
    model: str = "gemini-live-2.5-flash-preview-native-audio-09-2025"  # Live API 模型
    send_sample_rate: int = 16000  # 上行音频采样率 (Hz)
    receive_sample_rate: int = 24000  # 下行音频采样率 (Hz)
    default_voice: str = "Zephyr"  # 默认 AI 语音
    session_resumption: bool = True  # 启用会话恢复支持断线重连
    input_transcription: bool = True  # 启用用户语音转录
    output_transcription: bool = True  # 启用 AI 语音转录
    trigger_tokens: int = 10000  # 上下文压缩触发阈值
    target_tokens: int = 512  # 压缩后目标 token 数
    save_voice_history: bool = True  # 是否将语音对话保存到聊天历史
    # Live Chat 用量限制
    free_user_agent_limit: int = 10000  # 免费用户累计可聊天的 agent 数
    sub_user_agent_limit: int = 10000  # 订阅用户累计可聊天的 agent 数
    free_user_max_session_duration: int = 60  # 免费用户单次会话最大时长（秒）
    sub_user_max_session_duration: int = 120  # 订阅用户单次会话最大时长（秒）
    free_user_total_duration_24h: int = 300  # 免费用户 24h 总时长限制（秒）
    sub_user_total_duration_24h: int = 1800  # 订阅用户 24h 总时长限制（秒）


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
    sentry: SentryConfig
    push_notification: PushNotificationConfig
    memory_extraction: MemoryExtractionConfig = field(
        default_factory=lambda: MemoryExtractionConfig()
    )
    fal: FalConfig = field(default_factory=FalConfig)
    gemini_live: GeminiLiveConfig = field(default_factory=GeminiLiveConfig)


def load_config(path: str) -> Config:
    config_path = Path(path)
    if not config_path.exists():
        print(f"config file {path} not found!")
        sys.exit(1)

    print(f"[CONFIG] Loading config from: {config_path.absolute()}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Handle nested app config with limits
    app_data = data.get("app", {})
    if "limits" in app_data and isinstance(app_data["limits"], dict):
        app_data["limits"] = AppConfig.LimitsConfig(**app_data["limits"])

    # Convert environment string to Environment enum if present
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
        sentry=SentryConfig(**data.get("sentry", {})),
        push_notification=PushNotificationConfig(**data.get("push_notification", {})),
        memory_extraction=MemoryExtractionConfig(
            **(data.get("memory_extraction") or {})
        ),
        fal=FalConfig(**data.get("fal", {})),
        gemini_live=GeminiLiveConfig(**data.get("gemini_live", {})),
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

    # 校验并自动修正 limits 配置
    limits = config.app.limits

    # 规则1: 游客语音生成次数应该等于聊天次数，否则以聊天次数为准
    if limits.guest_user_voice_24h_limit != limits.guest_user_chat_24h_limit:
        logger.warning(
            f"Config issue: guest_user_voice_24h_limit ({limits.guest_user_voice_24h_limit}) "
            f"!= guest_user_chat_24h_limit ({limits.guest_user_chat_24h_limit}). "
            f"Auto-correcting to {limits.guest_user_chat_24h_limit}"
        )
        limits.guest_user_voice_24h_limit = limits.guest_user_chat_24h_limit

    # 规则2: 登录用户语音生成次数应该等于聊天次数，否则以聊天次数为准
    if limits.free_user_voice_24h_limit != limits.free_user_chat_24h_limit:
        logger.warning(
            f"Config issue: free_user_voice_24h_limit ({limits.free_user_voice_24h_limit}) "
            f"!= free_user_chat_24h_limit ({limits.free_user_chat_24h_limit}). "
            f"Auto-correcting to {limits.free_user_chat_24h_limit}"
        )
        limits.free_user_voice_24h_limit = limits.free_user_chat_24h_limit

    # 规则3: 游客聊天次数应该 <= 登录用户，否则使用默认值
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
        # 同步修正语音限制
        limits.guest_user_voice_24h_limit = default_guest
        limits.free_user_voice_24h_limit = default_free

    if (
        config.app.environment != Environment.TEST
        and limits.test_only_guest_user_image_gen_24h_limit > 0
    ):
        raise ValueError(
            "test_only_guest_user_image_gen_24h_limit is only allowed in test environment"
        )


DEFAULT_CONFIG_PATH = "config.yaml"
if not os.path.exists(DEFAULT_CONFIG_PATH):
    raise FileNotFoundError(
        f"{DEFAULT_CONFIG_PATH} 不存在，倒入本模块前请先创建配置文件"
    )
global_config_loaded_from_config_yaml = load_config(DEFAULT_CONFIG_PATH)
print(f"[CONFIG] Database URL: {global_config_loaded_from_config_yaml.database.url}")
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
