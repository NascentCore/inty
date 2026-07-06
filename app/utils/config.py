"""Application configuration

Use Pydantic models, instead of dataclass.
"""

import os
import sys
from datetime import datetime
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any, List, Optional

import yaml
from loguru import logger
from pydantic import (
    AliasChoices,
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.utils import models_catalog
from app.core.companion_harness.experience_profile.context_mode import (
    normalize_experience_profile_id,
)
from app.utils.companion_feature_defaults import (
    DEFAULT_COMPANION_FEATURE_COMPACTION,
)

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
# Chat LLM is invoked via OpenAI client (app.core.llms.openai_client) against OpenRouter (agent.base_url / agent.api_key).
# Model IDs are OpenRouter model names, e.g. google/gemini-2.5-flash-lite (GEMINI_2_5_FLASH_LITE), google/gemini-2.5-flash (GEMINI_2_5_FLASH).

GEMINI_2_5_FLASH = models_catalog.GEMINI_2_5_FLASH.id_on_provider
GEMINI_2_5_FLASH_LITE = models_catalog.GEMINI_2_5_FLASH_LITE.id_on_provider
VERTEX_AI_IMAGEN_4 = models_catalog.IMAGEN_4.id_on_provider
VERTEX_AI_IMAGEN_4_FAST = models_catalog.IMAGEN_4_FAST.id_on_provider


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


LOGGING_TIME_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS ZZ}"
LOGGING_LEVEL_FORMAT = "{level: <8}"
LOGGING_FILE_FORMAT = "{extra[inty_rel_file]}:{line} {function}"
LOGGING_MESSAGE_FORMAT = "{message}"


class LoggingConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    level: str = "INFO"
    # 默认格式，不使用颜色；路径为仓库根相对路径（由 init_logger 的 patcher 写入 extra[inty_rel_file]）
    format: str = (
        f"{LOGGING_TIME_FORMAT} | {LOGGING_LEVEL_FORMAT} | {LOGGING_FILE_FORMAT} - {LOGGING_MESSAGE_FORMAT}"
    )
    # 是否使用颜色
    colorize: bool = False

    @model_validator(mode="after")
    def apply_colorized_format(self) -> "LoggingConfig":
        if self.colorize:
            # 区分四块：时间=绿，级别=按级别着色，位置=品红(含完整路径)，正文=白
            self.format = f"<green>{LOGGING_TIME_FORMAT}</green> | <level>{LOGGING_LEVEL_FORMAT}</level> | <magenta>{LOGGING_FILE_FORMAT}</magenta> - <white>{LOGGING_MESSAGE_FORMAT}</white>"
        return self


class SecurityConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # This config cannot be changed after it's deployed, otherwise the existing tokens will be invalid.
    # This is because the token is encrypted using this secret key.
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days


class DatabaseSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

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
    # 未指定时 fall back 到 host
    replica_host: Optional[str] = None
    replica_port: int = 5432

    @property
    def url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def async_url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def async_replica_url(self) -> Optional[str]:
        if not self.replica_host:
            return None
        port = self.replica_port if self.replica_port is not None else self.port
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.replica_host}:{port}/{self.db}"
        )


class GoogleOAuthConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None


class VerificationConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code_expire_minutes: int = 5


class APIEndpointsConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    disable_api_v1_chat_completions: bool = False
    # 使用虚假的 Google 登录接口，用于测试，设为 True 时可以在 auth.py 中直接定义返回值来支持 app 前端测试。
    use_dummy_api_v1_auth_google_login: bool = False
    use_dummy_api_v1_character_themes_get: bool = False
    use_dummy_api_v1_character_themes_id_get: bool = False


class CompanionMemoryBootstrapType(StrEnum):
    """WS companion MemoryStore bootstrap mode (agent.companion_harness.memory_bootstrap_type)."""

    NONE = "NONE"
    USER_INTERACTIVE = "USER_INTERACTIVE"


class DreamingCuratorMode(StrEnum):
    """DreamingBatch MemoryDoc curation strategy (agent.companion_harness.dreaming_curator_mode).

    ``one_shot``: one LLM request with parallel tool calls for all target docs.
    ``sequential``: legacy per-document curator chain (rollback if one_shot quality regresses).
    See ``app.core.companion_harness.memory.dreaming_consolidation``.
    """

    SEQUENTIAL = "sequential"
    ONE_SHOT = "one_shot"


def _normalize_companion_memory_bootstrap_type(
    raw: str,
    *,
    config_path: str,
) -> str:
    normalized = (raw or "").strip().upper()
    allowed = {member.value for member in CompanionMemoryBootstrapType}
    if normalized not in allowed:
        raise ValueError(
            f"{config_path} must be one of {sorted(allowed)}, got {raw!r}"
        )
    return normalized


def _validate_companion_transcript_llm_window_max_messages(
    window_max_messages: Optional[int],
    *,
    config_path: str,
) -> None:
    if window_max_messages is None:
        return
    if window_max_messages < 2 or window_max_messages > 500:
        raise ValueError(f"{config_path} must be between 2 and 500")


def _validate_companion_transcript_compaction(
    compaction: Optional[dict[str, Any]],
) -> None:
    if compaction is None:
        return
    from app.core.companion_harness.memory.transcript_compaction import (
        CompactionConfig as CompanionTranscriptCompactionConfig,
    )

    CompanionTranscriptCompactionConfig.model_validate(compaction)


def _validate_companion_tool_bg_idle_wait_timeout_sec(
    timeout_sec: float,
    *,
    config_path: str,
) -> None:
    if timeout_sec < 1.0 or timeout_sec > 3600.0:
        raise ValueError(f"{config_path} must be between 1 and 3600")


def _validate_companion_implicit_sign_on_greeting_llm_timeout_sec(
    timeout_sec: float,
    *,
    config_path: str,
) -> None:
    if timeout_sec < 1.0 or timeout_sec > 60.0:
        raise ValueError(f"{config_path} must be between 1 and 60")


def _validate_companion_implicit_sign_on_greeting_llm_max_attempts(
    max_attempts: int,
    *,
    config_path: str,
) -> None:
    if max_attempts < 1 or max_attempts > 5:
        raise ValueError(f"{config_path} must be between 1 and 5")


def _validate_companion_proactive_chat_base_idle_seconds(
    base_idle_seconds: float,
    *,
    config_path: str,
) -> None:
    if base_idle_seconds < 10.0 or base_idle_seconds > 3600.0:
        raise ValueError(f"{config_path} must be between 10 and 3600")


def _validate_companion_proactive_chat_stop_after_silence_minutes(
    stop_after_silence_minutes: float,
    *,
    config_path: str,
) -> None:
    if stop_after_silence_minutes < 1.0 or stop_after_silence_minutes > 1440.0:
        raise ValueError(f"{config_path} must be between 1 and 1440")


class FeaturesConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    experimental_enable_chat_with_user_time_context: bool = True
    # 开关：是否启用自拍画像结论（后台推断 + 聊天提示词注入）
    enable_selfie_persona_summary: bool = True
    # Chat WebSocket: max seconds to wait for the next text frame before closing (ping/pong resets the wait).
    # Long-running LLM or tools do not extend this window unless the client sends ping or another frame.
    chat_ws_idle_timeout_seconds: int = 60

    @model_validator(mode="after")
    def validate_feature_ranges(self) -> "FeaturesConfig":
        """Range checks formerly in ``_validate_config`` (CFG-PYD-OPT-01c)."""
        ws_idle = self.chat_ws_idle_timeout_seconds
        if ws_idle < 10 or ws_idle > 3600:
            raise ValueError(
                "app.features.chat_ws_idle_timeout_seconds must be between 10 and 3600"
            )
        return self


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = "inty-backend"
    # TODO(issues/3688): Clarify or decouple debug from OpenAPI/docs once /docs endpoints are removed from all backends.
    # OpenAPI/docs and some non-fatal init failures (e.g. optional Firebase). Log level is not tied to this flag; use logging.level / INTY_* env.
    debug: bool = False
    # DEPRECATED: Do not use.
    debug_messages: bool = True
    # Use JSON format for request/response logging. Default is True (JSON format).
    use_json_log_format: bool = True
    backend_cors_origins: Optional[list[AnyHttpUrl]] = None
    version: str = "1.1.0"
    environment: Environment = Environment.DEV
    # 所有 Google 服务（GCP 及其他）都使用该身份信息来访问：GCS、Vertex AI
    gcp_service_account_key: str = ".secrets/inty-backend-key.json"
    api_v1_prefix: str = "/api/v1"
    # 仅当请求头 appVersionCode >= 此值时返回记忆提醒（消息列表 festival_memory_prompt、角色详情 festival_memories）；小于此值按旧版不返回。0 表示不按版本限制。
    min_app_version_code_for_festival_memory: int = 0
    # 仅当请求头 appVersionCode >= 此值时返回日常记忆提醒（消息列表 daily_memory_prompt、角色详情 daily_memories）；小于此值按旧版不返回。0 表示不按版本限制。
    min_app_version_code_for_daily_memory: int = 0

    api_endpoints: APIEndpointsConfig = Field(
        default_factory=APIEndpointsConfig
    )
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)

    class LimitsConfig(BaseModel):
        model_config = ConfigDict(extra="ignore")

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
        # LLM 对话时写入消息窗口（history window）的最大消息数（不包含 system messages）
        free_user_chat_messages_limit: int = 10
        sub_user_chat_messages_limit: int = 1000
        guest_user_chat_24h_limit: int = 10
        free_user_voice_24h_limit: int = 100
        guest_user_voice_24h_limit: int = 10
        subscribed_user_voice_24h_limit: int = 100
        free_user_music_gen_24h_limit: int = 2
        subscribed_user_music_gen_24h_limit: int = 6
        image_compression_threshold_size_kb: int = 500

        @model_validator(mode="after")
        def auto_correct_voice_and_guest_limits(
            self,
        ) -> "AppConfig.LimitsConfig":
            """Sync voice limits to chat limits; reset guest>free to defaults."""
            if (
                self.guest_user_voice_24h_limit
                != self.guest_user_chat_24h_limit
            ):
                logger.warning(
                    "Config issue: guest_user_voice_24h_limit "
                    f"({self.guest_user_voice_24h_limit}) "
                    f"!= guest_user_chat_24h_limit ({self.guest_user_chat_24h_limit}). "
                    f"Auto-correcting to {self.guest_user_chat_24h_limit}"
                )
                self.guest_user_voice_24h_limit = self.guest_user_chat_24h_limit

            if self.free_user_voice_24h_limit != self.free_user_chat_24h_limit:
                logger.warning(
                    "Config issue: free_user_voice_24h_limit "
                    f"({self.free_user_voice_24h_limit}) "
                    f"!= free_user_chat_24h_limit ({self.free_user_chat_24h_limit}). "
                    f"Auto-correcting to {self.free_user_chat_24h_limit}"
                )
                self.free_user_voice_24h_limit = self.free_user_chat_24h_limit

            if self.guest_user_chat_24h_limit > self.free_user_chat_24h_limit:
                default_guest = 10
                default_free = 100
                logger.warning(
                    "Config issue: guest_user_chat_24h_limit "
                    f"({self.guest_user_chat_24h_limit}) "
                    f"> free_user_chat_24h_limit ({self.free_user_chat_24h_limit}). "
                    f"Auto-correcting to defaults: guest={default_guest}, "
                    f"free={default_free}"
                )
                self.guest_user_chat_24h_limit = default_guest
                self.free_user_chat_24h_limit = default_free
                self.guest_user_voice_24h_limit = default_guest
                self.free_user_voice_24h_limit = default_free

            return self

    limits: LimitsConfig = Field(default_factory=LimitsConfig)

    @model_validator(mode="after")
    def ensure_nested_defaults(self) -> "AppConfig":
        if self.limits is None:
            self.limits = self.LimitsConfig()
        if self.features is None:
            self.features = FeaturesConfig()
        return self

    @property
    def name_for_openrouter(self) -> str:
        # https:// is required to make it recognized by open router.
        # Normal string will be rejected by open router.
        return f"https://{self.name}-{self.environment.value}"


class EmbeddingConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    base_url: str = "http://localhost:8001/v1"
    api_key: str = "sk-proj-1234567890"
    model: str = "DMetaSoul/Dmeta-embedding-zh-small"


class TelegramChannelConfig(BaseModel):
    """Ops Telegram channel Bot API credentials."""

    model_config = ConfigDict(extra="ignore")

    bot_token: str = ""


class SmsChannelConfig(BaseModel):
    """Ops SMS gateway long code and routing settings."""

    model_config = ConfigDict(extra="ignore")

    from_number: str = ""
    webhook_base_url: str = Field(
        default="",
        description=(
            "Public HTTPS origin for Twilio webhook signature validation "
            "(e.g. https://ops.example.com). Empty uses the inbound request URL."
        ),
    )


class AgentChannelsConfig(BaseModel):
    """Per-channel settings under agent (prototype: telegram only + weixin TODO)."""

    model_config = ConfigDict(extra="ignore")

    telegram: TelegramChannelConfig = Field(
        default_factory=TelegramChannelConfig
    )
    sms: SmsChannelConfig = Field(default_factory=SmsChannelConfig)
    # TODO(telegram-channel-config-weixin): move root ``weixin_channel`` (WeixinChannelConfig)
    # under ``agent.channels.weixin`` for symmetry.


def resolved_telegram_bot_token(agent: "AgentConfig") -> str:
    """Return ``agent.channels.telegram.bot_token``."""
    return agent.channels.telegram.bot_token.strip()


def resolved_sms_from_number(agent: "AgentConfig") -> str:
    """Return ``agent.channels.sms.from_number``."""
    return agent.channels.sms.from_number.strip()


def resolved_sms_twilio_webhook_url(
    agent: "AgentConfig",
    *,
    path: str,
) -> str:
    """Return configured public webhook URL for Twilio signature validation."""
    assert path.startswith("/")
    base = agent.channels.sms.webhook_base_url.strip().rstrip("/")
    if not base:
        return ""
    return f"{base}{path}"


def resolved_twilio_messaging_credentials(
    config: "Config",
) -> tuple[str, str]:
    """Return Twilio REST credentials shared by phone-call and SMS gateways."""
    account_sid = config.phone_call.twilio_account_sid.strip()
    auth_token = config.phone_call.twilio_auth_token.strip()
    return account_sid, auth_token


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # OpenRouter API key; chat is invoked via OpenAI client (app.core.llms.openai_client) against base_url.
    api_key: str = Field(...)
    langchain_api_key: str = Field(...)
    # DEPRECATED: Do not use. Use free_user_chat_model and sub_user_chat_model instead.
    model: str = GEMINI_2_5_FLASH
    # Free users: default chat model (OpenRouter model id), invoked via OpenAI client + OpenRouter.
    free_user_chat_model: str = GEMINI_2_5_FLASH_LITE
    # Subscribed users: default chat model (OpenRouter model id), invoked via OpenAI client + OpenRouter.
    sub_user_chat_model: str = GEMINI_2_5_FLASH
    # Companion WS tool-call route model id (passed to OpenAI-compatible gateway via
    # CompanionLLMConfig.tool_model). Independent of foreground chat envelope model so
    # the dual-LLM tool loop can scale separately. Empty string falls back to the chat
    # model at companion_chat_service wiring time (resolved_chat_model GenAIModel).
    # TODO(!3398): If user chat stays single-LLM, this applies mainly to inner-tick tool_background.
    # TODO: Move this config entry into CompanionHarnessConfig.
    companion_tool_call_model: str = "xiaomi/mimo-v2.5"
    # 免费用户商业化触达：定期返回一条“付费专属预览”消息并引导订阅。
    enable_free_user_premium_preview: bool = False
    # 触发频率（按聊天次数）：例如 5 表示每 5 条聊天触发一次；<=0 表示关闭。
    free_user_premium_preview_every_n_messages: int = 5
    # 预览文案最大长度（字符）。
    free_user_premium_preview_max_chars: int = 280
    # Note: Model selection is handled by app.core.model_selection.select_chat_model(),
    # which automatically chooses between free_user_chat_model and sub_user_chat_model
    # based on user subscription status and superuser privileges.
    # 下面的代码文件不需要检测订阅状态，因为 evaluation 是做评测，不部面向用户
    # - app/services/evaluation_service.py (updated to use select_chat_model)
    # OpenAI-compatible endpoint; use OPENROUTER_BASE_URL to invoke e.g. google/gemini-2.5-flash-lite via OpenRouter.
    # TODO(abstraction): Can be removed, replaced with GenAIModel with embedded provider.
    base_url: str = OPENROUTER_BASE_URL
    channels: AgentChannelsConfig = Field(default_factory=AgentChannelsConfig)

    class CompanionHarnessConfig(BaseModel):
        model_config = ConfigDict(extra="ignore")

        # TODO(#3673): Browserbase config (enabled, project_id); BROWSERBASE_API_KEY via env — epic #3672.
        # TODO: Change to Chinese OSS model when releasing to prod.
        dreaming_llm: str = Field(
            default="xiaomi/mimo-v2.5",
            description="The model to use for dreaming.",
        )
        dreaming_idle_seconds: int = Field(
            default=7200,
            ge=1,
            description=(
                "Min seconds since the latest real user message before "
                "``dreaming_due`` may run. Independent of the once-per-UTC-day cap "
                "(see ``companion.dreaming`` module doc)."
            ),
        )
        dreaming_curator_mode: DreamingCuratorMode = Field(
            default=DreamingCuratorMode.ONE_SHOT,
            description=(
                "DreamingBatch MemoryDoc curation: ``one_shot`` (single LLM with "
                "parallel tool calls) or ``sequential`` (legacy per-doc chain). "
                "Set ``sequential`` to roll back if one_shot quality regresses."
            ),
        )
        agent_scope_idle_timeout_minutes: int = Field(
            default=960,
            ge=1,
            description=(
                "Minutes since the latest user-activity anchor before a "
                "companion agent scope's runtime is paused to save tokens/CPU."
            ),
        )
        default_context_mode: str = Field(
            default="intimate",
            description=(
                "Default experience profile id (context.json field context_mode)."
            ),
        )
        memory_bootstrap_type: str = Field(
            default=CompanionMemoryBootstrapType.USER_INTERACTIVE.value,
            description=(
                "NONE = seed minimal docs only, always run_turn; "
                "USER_INTERACTIVE = run_turn with slice tools until bootstrap complete."
            ),
        )
        default_user_time_zone: str | None = Field(
            default=None,
            description=(
                "TEMPORARY launch fallback: IANA timezone when client and USER.md "
                "provide none. Remove after issues/3586."
            ),
        )
        language: str | None = Field(
            default=None,
            description=(
                "When set, all user-facing AgenticLoop replies use this language "
                "(e.g. English). None keeps reply language aligned with user messages."
            ),
        )

        @field_validator("language")
        @classmethod
        def _validate_language(cls, value: str | None) -> str | None:
            if value is None:
                return None
            stripped = value.strip()
            if stripped == "":
                return None
            return stripped

        @field_validator("default_user_time_zone")
        @classmethod
        def _validate_default_user_time_zone(
            cls, value: str | None
        ) -> str | None:
            if value is None:
                return None
            stripped = value.strip()
            if stripped == "":
                return None
            from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

            try:
                return ZoneInfo(stripped).key
            except ZoneInfoNotFoundError as exc:
                raise ValueError(
                    "agent.companion_harness.default_user_time_zone "
                    f"invalid IANA name: {stripped!r}"
                ) from exc

        class TranscriptConfig(BaseModel):
            model_config = ConfigDict(extra="ignore")

            compaction: Optional[dict[str, Any]] = Field(
                default_factory=lambda: dict(
                    DEFAULT_COMPANION_FEATURE_COMPACTION
                ),
                description=(
                    "OpenAI message-list compaction for companion kernel. "
                    "Set to null in YAML to disable."
                ),
            )
            llm_window_max_messages: Optional[int] = Field(
                default=None,
                description=(
                    "Max transcript rows loaded before compaction "
                    "(default: kernel TRANSCRIPT_WINDOW_MAX_MESSAGES)."
                ),
            )

        transcript: TranscriptConfig = Field(default_factory=TranscriptConfig)

        class WsConfig(BaseModel):
            model_config = ConfigDict(extra="ignore")

            session_system_text: Optional[str] = Field(
                default=None,
                description=(
                    "Overrides default text for the one-shot system row on first "
                    "USER_INTERACTIVE WS turn."
                ),
            )

        ws: WsConfig = Field(default_factory=WsConfig)

        class InnerTickConfig(BaseModel):
            model_config = ConfigDict(extra="ignore")

            class ProactiveChatConfig(BaseModel):
                model_config = ConfigDict(extra="ignore")

                base_idle_seconds: float = Field(
                    default=30.0,
                    description=(
                        "Base quiet period before proactive chat may fire; rhythm "
                        "adapts from real-user gaps up to 2× this value."
                    ),
                )
                stop_after_silence_minutes: float = Field(
                    default=30.0,
                    description=(
                        "Stop proactive chat when silence since last real user "
                        "message exceeds this many minutes."
                    ),
                )
                poll_seconds: float = Field(
                    default=60.0,
                    description=(
                        "Seconds between unified inner-tick worker wakeups "
                        "(proactive + monolog eligibility checks)."
                    ),
                )

            class MonologConfig(BaseModel):
                model_config = ConfigDict(extra="ignore")

                min_gap_seconds: float = Field(
                    default=120.0,
                    description=(
                        "Minimum seconds between successful monolog inner-tick "
                        "fires."
                    ),
                )

            proactive_chat: ProactiveChatConfig = Field(
                default_factory=ProactiveChatConfig
            )
            monolog: MonologConfig = Field(
                default_factory=MonologConfig,
                validation_alias=AliasChoices("monolog", "maintenance"),
            )

        inner_tick: InnerTickConfig = Field(default_factory=InnerTickConfig)

        tool_bg_idle_wait_timeout_sec: float = Field(
            default=120.0,
            description=(
                "Seconds to wait on CompanionSession.tool_bg_idle before LivingSphere "
                "jsonl compact."
            ),
        )

        class ImplicitSignOnGreetingConfig(BaseModel):
            model_config = ConfigDict(extra="ignore")

            llm_timeout_sec: float = Field(
                default=12.0,
                description=(
                    "Implicit user_signed_on greeting: per-attempt LLM wait."
                ),
            )
            llm_max_attempts: int = Field(
                default=2,
                description=(
                    "Max LLM attempts for implicit sign-on greeting "
                    "(includes the first call; 2 = one retry)."
                ),
            )

        implicit_sign_on_greeting: ImplicitSignOnGreetingConfig = Field(
            default_factory=ImplicitSignOnGreetingConfig
        )

        class UserFeedbackGithubConfig(BaseModel):
            repo: str = Field(
                default="nascentcore/inty",
                description="GitHub repo (owner/name) for companion user-feedback issues.",
            )
            token: str = Field(
                default="",
                description=(
                    "GitHub PAT for ``companion_record_user_feedback`` issue creation; "
                    "empty uses ``GH_TOKEN`` env; both empty skips issue filing."
                ),
            )

        user_feedback_github: UserFeedbackGithubConfig = Field(
            default_factory=UserFeedbackGithubConfig
        )

        class UserTurnConfig(BaseModel):
            llm_loop_mode: str = Field(
                default="dual_llm",
                description=(
                    "Settled user-chat agentic loop mode: "
                    "in_turn_single_llm | dual_llm"
                ),
            )
            batch_user_messages_llm_call_mode: str = Field(
                default="MULTI_USER_MESSAGES",
                description=(
                    "How a claimed InputQueue batch is represented in one "
                    "user-turn LLM call: "
                    "JOIN_TO_ONE_USER_MESSAGE | MULTI_USER_MESSAGES"
                ),
            )

            @field_validator("llm_loop_mode")
            @classmethod
            def _validate_llm_loop_mode(cls, value: str) -> str:
                from app.core.companion_harness.loop.config import (
                    UserTurnLlmLoopMode,
                )

                UserTurnLlmLoopMode(value)
                return value

            @field_validator("batch_user_messages_llm_call_mode")
            @classmethod
            def _validate_batch_user_messages_llm_call_mode(
                cls, value: str
            ) -> str:
                from app.core.companion_harness.loop.config import (
                    BatchUserMessagesLlmCallMode,
                )

                BatchUserMessagesLlmCallMode(value)
                return value

        user_turn: UserTurnConfig = Field(default_factory=UserTurnConfig)

        @model_validator(mode="after")
        def normalize_companion_fields(
            self,
        ) -> "AgentConfig.CompanionHarnessConfig":
            self.memory_bootstrap_type = (
                _normalize_companion_memory_bootstrap_type(
                    self.memory_bootstrap_type,
                    config_path="agent.companion_harness.memory_bootstrap_type",
                )
            )
            self.default_context_mode = normalize_experience_profile_id(
                self.default_context_mode
            )
            return self

        @model_validator(mode="after")
        def validate_companion_ranges(
            self,
        ) -> "AgentConfig.CompanionHarnessConfig":
            _validate_companion_transcript_llm_window_max_messages(
                self.transcript.llm_window_max_messages,
                config_path=(
                    "agent.companion_harness.transcript.llm_window_max_messages"
                ),
            )
            _validate_companion_transcript_compaction(
                self.transcript.compaction
            )
            _validate_companion_tool_bg_idle_wait_timeout_sec(
                self.tool_bg_idle_wait_timeout_sec,
                config_path="agent.companion_harness.tool_bg_idle_wait_timeout_sec",
            )
            _validate_companion_implicit_sign_on_greeting_llm_timeout_sec(
                self.implicit_sign_on_greeting.llm_timeout_sec,
                config_path=(
                    "agent.companion_harness.implicit_sign_on_greeting.llm_timeout_sec"
                ),
            )
            _validate_companion_implicit_sign_on_greeting_llm_max_attempts(
                self.implicit_sign_on_greeting.llm_max_attempts,
                config_path=(
                    "agent.companion_harness.implicit_sign_on_greeting.llm_max_attempts"
                ),
            )
            _validate_companion_proactive_chat_base_idle_seconds(
                self.inner_tick.proactive_chat.base_idle_seconds,
                config_path=(
                    "agent.companion_harness.inner_tick.proactive_chat.base_idle_seconds"
                ),
            )
            _validate_companion_proactive_chat_stop_after_silence_minutes(
                self.inner_tick.proactive_chat.stop_after_silence_minutes,
                config_path=(
                    "agent.companion_harness.inner_tick.proactive_chat"
                    ".stop_after_silence_minutes"
                ),
            )
            return self

    companion_harness: CompanionHarnessConfig = Field(
        default_factory=CompanionHarnessConfig
    )
    # Chat 专用 LLM 端点（可选）。若两者均配置则 Agent 聊天使用此端点，否则使用 base_url + api_key。记忆抽取始终使用 base_url + api_key。
    # TODO(abstraction): Can be removed, replaced with GenAIModel with embedded provider.
    chat_llm_base_url: Optional[str] = None
    # TODO(abstraction): Can be removed, replaced with GenAIModel with embedded provider.
    chat_llm_api_key: Optional[str] = None
    # Chat 使用的 LLM 网关标识，用于 meta_data.llm_provider；可选值为 openrouter / litellm。
    # TODO(abstraction): Can be removed, replaced with GenAIModel with embedded provider.
    chat_llm_provider: str = "openrouter"
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    top_k: int = 50
    frequency_penalty: float = 0.5
    presence_penalty: float = 0.5
    # DEPRECATED: Do not use.
    enable_debug_logging: bool = False  # 是否启用调试日志记录功能
    # 是否向 LangSmith 上报 trace（应用启动时写入 LANGSMITH_TRACING_V2）。
    # 关闭时仍会设置 LANGSMITH_PROJECT / LANGCHAIN_API_KEY，仅 tracing 为 false。
    langsmith_tracing_enabled: bool = True
    # LangSmith 文本聊天追踪采样率（0.0-1.0）。
    # 实际生效值在调用处会被限制到 <=10%，避免文本聊天成功请求过量追踪。
    # 文本聊天的失败概率也极低，因此不需要特别关注错误信息。
    # 图片生成不使用该采样率限制，保持全量追踪。
    langsmith_text_chat_sample_rate: float = 0.1
    # 若用户邮箱命中该名单，则文本聊天调用始终写入 LangSmith trace（忽略采样率）。
    langsmith_text_chat_always_trace_user_emails: list[str] = Field(
        default_factory=list
    )
    # 官方 IntelliMate 助手的对话历史窗口条数（不按订阅分档，仅此一个限制）
    official_assistant_chat_messages_limit: int = 50

    # TODO: 这是做什么的？
    vertex_image_model: str = VERTEX_AI_IMAGEN_4_FAST

    free_user_text_to_image_model: Optional[str] = VERTEX_AI_IMAGEN_4_FAST
    sub_user_text_to_image_model: Optional[str] = VERTEX_AI_IMAGEN_4
    force_default_prompts: bool = (
        False  # 强制使用默认提示词，忽略Agent自定义提示词
    )
    enable_christmas_prompt: bool = False  # 是否启用圣诞节季节性提示词
    # 图片生成配置
    image_generation_default_history_count: int = 10
    music_generation_default_history_count: int = 10
    # 消息生图失败时是否匹配已生成图片作为兜底
    enable_chat_image_match_fallback: bool = False
    # 消息生图（chat image）模型配置：使用 models_catalog 中模型的 nickname
    free_user_chat_image_model: str = "Nano Banana"
    sub_user_chat_image_model: str = "Nano Banana"
    # 消息生音乐（chat music）模型配置：当前使用 fal 模型 ID
    free_user_chat_music_model: str = "fal-ai/stable-audio"
    sub_user_chat_music_model: str = "fal-ai/stable-audio"
    # 聊天 TTS（Gemini TTS 模型 ID）；选择逻辑见 select_chat_tts_model()
    free_user_chat_tts_model: str = "gemini-2.5-flash-tts"
    sub_user_chat_tts_model: str = "gemini-2.5-pro-tts"
    # 用户自拍画像推断模型（用于生成简短用户画像结论）
    selfie_persona_gemini_model: str = "gemini-2.5-flash"
    # 订阅用户首轮生图遇 429 时重试使用的 Vertex 模型 ID
    sub_user_chat_image_gemini_fallback_model: str = "gemini-2.5-flash-image"
    # 消息生图选用 models_catalog「NewAPI Nano Banana 2」时的网关根地址；/v1beta/models/...；仅 origin，勿带 /v1beta
    newapi_gemini_base_url: Optional[str] = None
    newapi_gemini_bearer_token: Optional[str] = (
        None  # 或使用环境变量 NEWAPI_GEMINI_BEARER_TOKEN
    )
    # Vertex AI 区域，用于 get_genai_client（消息生图、记忆抽取等）
    # 设为 "global" 可改善 gemini-3-pro-image-preview 等 Preview 模型的可用性
    vertex_ai_location: str = "us-central1"
    # 视频生成配置
    veo3_model: str = "veo-3.0-fast-generate-preview"  # Veo3 模型名称
    # 动图配置
    animated_image_max_size_mb: int = 10  # 动图文件大小限制（MB）
    animated_image_fps: int = 15  # 动图帧率
    animated_image_max_width: int = 720  # 动图最大宽度
    preferred_animated_format: str = "avif"  # 首选格式：avif 或 gif
    # Agent 聊天轻量数据缓存 TTL（秒）；短 TTL 便于 ops 与后端分离部署时读到最新数据
    agent_config_cache_ttl_seconds: int = 20 * 60  # 默认 20 分钟

    @model_validator(mode="after")
    def validate_agent_fields(self) -> "AgentConfig":
        """Checks formerly in ``_validate_config`` (CFG-PYD-OPT-01d/e)."""
        if self.chat_llm_provider not in ("openrouter", "litellm"):
            raise ValueError(
                "agent.chat_llm_provider must be 'openrouter' or 'litellm', "
                f"got: {self.chat_llm_provider!r}"
            )
        if (self.newapi_gemini_base_url or "").strip():
            tok = (self.newapi_gemini_bearer_token or "").strip() or (
                os.environ.get("NEWAPI_GEMINI_BEARER_TOKEN") or ""
            ).strip()
            if not tok:
                raise ValueError(
                    "agent.newapi_gemini_bearer_token or NEWAPI_GEMINI_BEARER_TOKEN "
                    "required when newapi_gemini_base_url is set"
                )
        return self


class GCSConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    bucket: str = "inty-storage"
    # DEPRECATED: 保留作为兼容；被 app.gcp_service_account_key 取代
    # 删除部署环境中的配置文件使用，然后删除这个代码。
    credentials: str = "<deprecated-do-not-use>"
    # 如果为 True，则使用假GCS客户端；在本地存储文件，不使用 GCS 服务。用于测试。
    use_fake_gcs: bool = False
    fake_gcs_base_dir: str = "/tmp/inty_fake_gcs"


class FirebaseConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    service_account_path: str = ".secrets/inty-backend-key.json"


class GooglePlayConfig(BaseModel):
    """Google Play配置"""

    model_config = ConfigDict(extra="ignore")

    # DEPRECATED: 保留作为兼容；被 app.gcp_service_account_key 取代
    # 删除部署环境中的配置文件使用，然后删除这个代码。
    service_account_key: str = ".secrets/inty-backend-key.json"
    package_name: str = "com.ai.intellimate"
    webhook_secret: Optional[str] = None  # Webhook密钥（可选）
    # 版本检查相关配置
    enable_version_check: bool = True  # 是否启用版本检查
    # DEPRECATED: 未被使用过。使用 force_update_version_code_gap 替代，可以取得类似的效果。
    min_supported_version: int = 1  # 最低支持版本代码
    # DEPRECATED: 未被使用过。
    # 删除部署环境中的配置文件使用，然后删除这个代码。
    release_track: str = (
        "production"  # 发布轨道：internal/closed/open/production
    )
    # DEPRECATED: 未被使用过。
    # 删除部署环境中的配置文件使用，然后删除这个代码。
    fallback_tracks: Optional[list[str]] = None  # 备用轨道列表
    # DEPRECATED: 不检查 version name，只检查 version code，这样使用简单的线性递增逻辑，很容易理解。
    max_minor_version_gap: int = 10  # Minor版本号最大差距，超过则强制更新
    # 当前生产环境版本代码（覆盖值）：
    # - 设置为正数时，版本检查直接使用此值，不调用 Google Play API（避免 edits.insert 配额消耗）
    # - 设置为 0 或未配置时，通过 Google Play API 动态获取版本信息
    current_version_code: int = 3277  # 当前 Google Play 生产环境的版本代码
    # 版本代码差距阈值配置；线性递增的多个阈值，超过某个阈值意味着之前超越的阈值的动作都会在 app 端执行。
    # 比如，触发 popup_reminder_version_code_gap 动作，意味着 settings reminder 与 popup reminder 都会在 app 端执行。
    force_update_version_code_gap: int = 1000  # 版本代码差距超过此值则强制更新
    popup_reminder_version_code_gap: int = (
        200  # 版本代码差距在此值以上则显示弹窗提醒
    )
    settings_reminder_version_code_gap: int = (
        1  # 版本代码差距在此值以上则显示设置提醒
    )


class CloudflareConfig(BaseModel):
    """Cloudflare CDN代理配置"""

    model_config = ConfigDict(extra="ignore")

    domain: str = ""  # Cloudflare代理的域名
    enabled: bool = False  # 是否启用Cloudflare CDN代理
    fallback_to_original: bool = True  # 转换失败时是否回退到原始URL


class ElevenLabsConfig(BaseModel):
    """ElevenLabs语音生成配置"""

    model_config = ConfigDict(extra="ignore")

    api_key: str = Field(...)
    model: str = "eleven_multilingual_v2"
    voice_id: str = "JBFqnCBsd6RMkjVDRZzb"  # 默认语音ID
    output_format: str = "mp3_44100_128"
    enabled: bool = True
    max_text_length: int = 5000  # 最大文本长度限制
    ssl_verify: bool = True  # SSL证书验证开关
    voice_change_model: str = "eleven_english_sts_v2"


class MemoryExtractionConfig(BaseModel):
    """记忆抽取配置（由 tools/scripts/run_memory_extraction.py 等手动入口使用）。"""

    model_config = ConfigDict(extra="ignore")

    class WorkflowMode(str, Enum):
        ALWAYS_SUMMARIZE_FULL_CHAT_MESSAGES_HISTORY = (
            "always_summarize_full_chat_messages_history"
        )
        DAILY_INCREMENTAL_SUMMARIZATION = "daily_incremental_summarization"

    model: str = (
        ""  # OpenRouter 模型 id，为空时使用代码内默认（mistralai/devstral-2512）
    )
    workflow_mode: WorkflowMode = (
        WorkflowMode.ALWAYS_SUMMARIZE_FULL_CHAT_MESSAGES_HISTORY
    )
    trigger_new_user_messages: int = (
        30  # 新用户总聊天次数阈值（subscription_usage）
    )
    trigger_incremental_messages: int = (
        30  # 已提取用户自上次后新增聊天次数阈值（subscription_usage）
    )
    # When companion kernel fills CompanionTurnResult.significance_perception, chat.py mirrors it
    # into chat_history AI meta_data. Enabling this sorts extraction input by
    # meta_data.significance_perception.importance_round and adds bracket hints for the extractor LLM.
    # Pipeline overview: app/core/companion_harness/companion/dual_llm_chat_branch_envelope.py module docstring.
    use_significance_perception_in_extraction: bool = False


class SurpriseSnapConfig(BaseModel):
    """Surprise Snap：用户与角色对话达到指定轮数时插入专属照消息。"""

    model_config = ConfigDict(extra="ignore")

    enabled_since: Optional[datetime] = (
        None  # 只统计此时间之后的用户消息；None 则不触发
    )
    trigger_rounds: List[int] = Field(
        default_factory=lambda: [3, 8, 15]
    )  # 用户消息数达到这些轮数时触发

    @field_validator("enabled_since", mode="before")
    @classmethod
    def parse_enabled_since(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return None
        if isinstance(value, datetime):
            return value
        return None

    @field_validator("trigger_rounds", mode="before")
    @classmethod
    def ensure_trigger_rounds_list(cls, value: object) -> object:
        if not isinstance(value, list):
            return [3, 8, 15]
        return value


class UserAnalyticsReportConfig(BaseModel):
    """用户分析预计算运行时参数。

    生产 IntelliMate 日报由 GitHub Actions
    ``daily_intellimate_user_activity_report.yaml`` 与
    ``tools/scripts/run_user_analytics_report.py`` 承担。
    """

    model_config = ConfigDict(extra="ignore")

    statement_timeout_sec: int = 600  # 单条 SQL 超时秒数，生产大数据量时需调大
    batch_size: int = (
        500  # 分批查询 session/chat 时每批数量，减小可降低 standby conflict with recovery
    )


class PushNotificationConfig(BaseModel):
    """推送通知服务配置"""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True  # 是否启用推送服务
    batch_size: int = 50  # 每批处理的聊天数量
    festival_memory_enabled: bool = True  # 是否启用节日记忆通知推送
    festival_memory_batch_size: int = (
        50  # 节日记忆通知每批处理的 (user_id, agent_id) 数量
    )
    max_retries: int = 3  # 最大重试次数
    max_concurrent_workers: int = 50  # 最大并发 worker 数
    workers_per_user_ratio: int = (
        10  # 每 N 个用户分配 1 个 worker（如 10 表示每 10 个用户 1 个 worker）
    )
    stages: Optional[dict[str, Any]] = (
        None  # 推送阶段策略配置（10min, 30min, 2h, 24h, 48h），有聊天记录和无聊天记录用户共用
    )

    @model_validator(mode="after")
    def apply_default_stages(self) -> "PushNotificationConfig":
        if self.stages is None:
            self.stages = {
                "10min": {"count": 0, "minutes": 10},
                "30min": {"count": 1, "minutes": 30},
                "2h": {"count": 2, "minutes": 120},
                "24h": {"count": 3, "hours": 24},
                "48h": {"count": 4, "hours": 48},
            }
        return self


class FalConfig(BaseModel):
    """fal.ai 生图服务配置"""

    model_config = ConfigDict(extra="ignore")

    api_key: str = ""  # fal.ai API key


class GeminiLiveConfig(BaseModel):
    """Gemini Live API 实时语音通话配置
    使用 Vertex AI 模式，复用 app.gcp_service_account_key 进行认证
    """

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False  # 是否启用实时语音通话功能
    project_id: str = "inty-backend"  # GCP 项目 ID
    location: str = "us-central1"  # Vertex AI 区域
    model: str = "gemini-live-2.5-flash-native-audio"  # Live API 模型
    send_sample_rate: int = 16000  # 上行音频采样率 (Hz)
    receive_sample_rate: int = 24000  # 下行音频采样率 (Hz)
    default_voice: str = "Zephyr"  # 默认 AI 语音
    # SpeechConfig.language_code（BCP-47），用于尽量固定语音合成语言
    speech_language_code: str = "en-US"
    # native-audio 模型主要通过 system instruction 约束回复语言
    response_language_name: str = "English"
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
    # Live chat 音频落盘临时目录，None 或空时使用 tempfile.gettempdir()
    audio_temp_dir: Optional[str] = None


class PhoneCallConfig(BaseModel):
    """PSTN phone-call bridge configuration.

    The feature flag defaults to on so product surfaces may show the capability,
    while runtime availability is still gated by Twilio/Gemini/public-WSS config.
    Secrets should be supplied by environment variables in deployments.
    """

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    default_country_code: str = "+1"
    twilio_from_number: str = ""
    twilio_media_stream_base_url: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    inbound_number_agent_map: dict[str, str] = Field(default_factory=dict)
    default_inbound_agent_id: str = ""
    media_stream_token_ttl_seconds: int = 300

    @model_validator(mode="after")
    def validate_phone_call_when_enabled(self) -> "PhoneCallConfig":
        """Range/format checks formerly in ``_validate_config`` (CFG-PYD-OPT-01b)."""
        if not self.enabled:
            return self
        if (
            self.media_stream_token_ttl_seconds < 60
            or self.media_stream_token_ttl_seconds > 3600
        ):
            raise ValueError(
                "phone_call.media_stream_token_ttl_seconds must be between 60 and 3600"
            )
        if (
            self.twilio_media_stream_base_url
            and not self.twilio_media_stream_base_url.startswith("wss://")
        ):
            raise ValueError(
                "phone_call.twilio_media_stream_base_url must start with wss://"
            )
        if (
            self.default_country_code
            and not self.default_country_code.startswith("+")
        ):
            raise ValueError(
                "phone_call.default_country_code must start with '+'"
            )
        return self


class TTSConfig(BaseModel):
    """语音播报配置"""

    model_config = ConfigDict(extra="ignore")

    # 测试环境启用 fake provider，避免 CI/本地测试依赖真实 TTS API。
    use_fake_tts: bool = False
    # Gemini tts 还不稳定，经常出现措辞失误：把括号里面内容讲出来、重复对话内容
    use_gemini_prompted_tts: bool = True
    # iMate 语音播报模式：
    # - dialogue_only: 仅朗读对白（默认，当前行为）
    # - dialogue_and_stage_directions: 朗读对白 + 括号内舞台说明
    voice_message_narration_mode: str = "dialogue_only"
    # 实验开关：ElevenLabs 目标音色走 Gemini 先合成，再 ElevenLabs speech-to-speech 变声
    # - 仅作用于 ElevenLabs 音色（11labs/...）；Gemini 音色不受影响
    # - 默认关闭，避免影响线上稳定路径
    enable_gemini_tts_then_elevenlabs_voice_changer_for_imate: bool = False


class WeixinChannelConfig(BaseModel):
    """Ops Weixin channel behavior flags."""

    model_config = ConfigDict(extra="ignore")

    # True: Hermes legacy per_line — top-level line breaks become separate WeChat DMs.
    # False (default): compact — single bubble unless short chatty multiline heuristic fires.
    split_multiline_messages: bool = False


class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")

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
    push_notification: PushNotificationConfig
    memory_extraction: MemoryExtractionConfig = Field(
        default_factory=MemoryExtractionConfig
    )
    user_analytics_report: UserAnalyticsReportConfig = Field(
        default_factory=UserAnalyticsReportConfig
    )
    fal: FalConfig = Field(default_factory=FalConfig)
    gemini_live: GeminiLiveConfig = Field(default_factory=GeminiLiveConfig)
    phone_call: PhoneCallConfig = Field(default_factory=PhoneCallConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    surprise_snap: SurpriseSnapConfig = Field(
        default_factory=SurpriseSnapConfig
    )
    weixin_channel: WeixinChannelConfig = Field(
        default_factory=WeixinChannelConfig
    )


_ROOT_CONFIG_OPTIONAL_YAML_SECTIONS = (
    "security",
    "database",
    "google_oauth",
    "verification",
    "logging",
    "embedding",
    "gcs",
    "firebase",
    "google_play",
    "elevenlabs",
    "cloudflare",
    "push_notification",
    "memory_extraction",
    "user_analytics_report",
    "fal",
    "gemini_live",
    "phone_call",
    "tts",
    "surprise_snap",
    "weixin_channel",
)


class RootConfig(Config):
    """YAML document root: single ``model_validate`` entry for ``load_config``."""

    @model_validator(mode="before")
    @classmethod
    def fill_missing_yaml_sections(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        for key in _ROOT_CONFIG_OPTIONAL_YAML_SECTIONS:
            if key not in normalized:
                normalized[key] = {}
        return normalized


# TODO(INTY_CONFIG_YAML): add resolve_inty_config_yaml_path() — INTY_CONFIG_YAML or config.yaml;
# used by app.core.config, backend/alembic/env.py, and standalone scripts.
# https://github.com/NascentCore/inty/issues/3530


def load_config(path: str) -> Config:
    """加载配置文件

    因为 logger 配置会先调用本函数，因此这里的日志格式还未生效。
    因此这里的日志会使用默认格式，不使用颜色。
    """
    config_path = Path(path)
    if not config_path.exists():
        logger.error(f"config file {path} not found!")
        sys.exit(1)

    logger.info(f"[CONFIG] Loading config from: {config_path.absolute()}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return RootConfig.model_validate(data or {})


# TODO(config): replace ``fill_missing_yaml_sections`` with ``Field(default_factory=...)`` on
# optional YAML sections so ``RootConfig`` needs no before-validator.


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

    # 消息生图模型 nickname 必须能解析为允许的模型
    models_catalog.must_resolve_nickname(
        config.agent.free_user_chat_image_model
    )
    models_catalog.must_resolve_nickname(config.agent.sub_user_chat_image_model)

    limits = config.app.limits

    if (
        config.app.environment != Environment.TEST
        and limits.test_only_guest_user_image_gen_24h_limit > 0
    ):
        raise ValueError(
            "test_only_guest_user_image_gen_24h_limit is only allowed in test environment"
        )
