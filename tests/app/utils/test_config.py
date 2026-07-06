import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.utils.companion_feature_defaults import (
    DEFAULT_COMPANION_FEATURE_COMPACTION,
)
from app.utils.config import (
    AgentConfig,
    APIEndpointsConfig,
    AppConfig,
    FeaturesConfig,
    CloudflareConfig,
    Config,
    DatabaseSettings,
    ElevenLabsConfig,
    EmbeddingConfig,
    Environment,
    FalConfig,
    FirebaseConfig,
    GCSConfig,
    GeminiLiveConfig,
    GoogleOAuthConfig,
    GooglePlayConfig,
    LoggingConfig,
    MemoryExtractionConfig,
    PushNotificationConfig,
    SecurityConfig,
    SurpriseSnapConfig,
    TTSConfig,
    UserAnalyticsReportConfig,
    VerificationConfig,
    _validate_config,
    load_config,
)
from app.core.companion_harness.loop.config import (
    BatchUserMessagesLlmCallMode,
)


@pytest.fixture
def config():
    return Config(
        app=AppConfig(
            name="test",
            environment=Environment.PROD,  # 非local环境
            limits=AppConfig.LimitsConfig(
                test_only_guest_user_image_gen_24h_limit=0,  # 合法配置
            ),
        ),
        security=SecurityConfig(secret_key="test"),
        database=DatabaseSettings(),
        google_oauth=GoogleOAuthConfig(),
        verification=VerificationConfig(),
        logging=LoggingConfig(),
        embedding=EmbeddingConfig(),
        agent=AgentConfig(api_key="test", langchain_api_key="test"),
        gcs=GCSConfig(bucket="test"),
        firebase=FirebaseConfig(service_account_path="test"),
        google_play=GooglePlayConfig(),
        elevenlabs=ElevenLabsConfig(api_key="test"),
        cloudflare=CloudflareConfig(),
        push_notification=PushNotificationConfig(),
    )


def test_guest_voice_auto_correction():
    """测试游客语音限制自动修正为聊天限制"""
    config = Config(
        app=AppConfig(
            name="test",
            limits=AppConfig.LimitsConfig(
                guest_user_chat_24h_limit=5,
                guest_user_voice_24h_limit=10,  # 错误配置
                free_user_chat_24h_limit=100,
                free_user_voice_24h_limit=100,
            ),
        ),
        security=SecurityConfig(secret_key="test"),
        database=DatabaseSettings(),
        google_oauth=GoogleOAuthConfig(),
        verification=VerificationConfig(),
        logging=LoggingConfig(),
        embedding=EmbeddingConfig(),
        agent=AgentConfig(api_key="test", langchain_api_key="test"),
        gcs=GCSConfig(bucket="test"),
        firebase=FirebaseConfig(service_account_path="test"),
        google_play=GooglePlayConfig(),
        elevenlabs=ElevenLabsConfig(api_key="test"),
        cloudflare=CloudflareConfig(),
        push_notification=PushNotificationConfig(),
    )

    _validate_config(config)

    # 应该自动修正为聊天限制
    assert config.app.limits.guest_user_voice_24h_limit == 5


def test_free_user_voice_auto_correction():
    """测试登录用户语音限制自动修正为聊天限制"""
    config = Config(
        app=AppConfig(
            name="test",
            limits=AppConfig.LimitsConfig(
                guest_user_chat_24h_limit=5,
                guest_user_voice_24h_limit=5,
                free_user_chat_24h_limit=100,
                free_user_voice_24h_limit=50,  # 错误配置
            ),
        ),
        security=SecurityConfig(secret_key="test"),
        database=DatabaseSettings(),
        google_oauth=GoogleOAuthConfig(),
        verification=VerificationConfig(),
        logging=LoggingConfig(),
        embedding=EmbeddingConfig(),
        agent=AgentConfig(api_key="test", langchain_api_key="test"),
        gcs=GCSConfig(bucket="test"),
        firebase=FirebaseConfig(service_account_path="test"),
        google_play=GooglePlayConfig(),
        elevenlabs=ElevenLabsConfig(api_key="test"),
        cloudflare=CloudflareConfig(),
        push_notification=PushNotificationConfig(),
    )

    _validate_config(config)

    assert config.app.limits.free_user_voice_24h_limit == 100


def test_guest_greater_than_free_auto_correction():
    """测试游客限制大于登录用户时自动使用默认值"""
    config = Config(
        app=AppConfig(
            name="test",
            limits=AppConfig.LimitsConfig(
                guest_user_chat_24h_limit=200,  # 错误配置
                guest_user_voice_24h_limit=200,
                free_user_chat_24h_limit=100,
                free_user_voice_24h_limit=100,
            ),
        ),
        security=SecurityConfig(secret_key="test"),
        database=DatabaseSettings(),
        google_oauth=GoogleOAuthConfig(),
        verification=VerificationConfig(),
        logging=LoggingConfig(),
        embedding=EmbeddingConfig(),
        agent=AgentConfig(api_key="test", langchain_api_key="test"),
        gcs=GCSConfig(bucket="test"),
        firebase=FirebaseConfig(service_account_path="test"),
        google_play=GooglePlayConfig(),
        elevenlabs=ElevenLabsConfig(api_key="test"),
        cloudflare=CloudflareConfig(),
        push_notification=PushNotificationConfig(),
    )

    _validate_config(config)

    # 应该使用默认值
    assert config.app.limits.guest_user_chat_24h_limit == 10
    assert config.app.limits.free_user_chat_24h_limit == 100
    assert config.app.limits.guest_user_voice_24h_limit == 10
    assert config.app.limits.free_user_voice_24h_limit == 100


def test_valid_config_no_changes():
    """测试合法配置不会被修改"""
    config = Config(
        app=AppConfig(
            name="test",
            limits=AppConfig.LimitsConfig(
                guest_user_chat_24h_limit=5,
                guest_user_voice_24h_limit=5,
                free_user_chat_24h_limit=10,
                free_user_voice_24h_limit=10,
            ),
        ),
        security=SecurityConfig(secret_key="test"),
        database=DatabaseSettings(),
        google_oauth=GoogleOAuthConfig(),
        verification=VerificationConfig(),
        logging=LoggingConfig(),
        embedding=EmbeddingConfig(),
        agent=AgentConfig(api_key="test", langchain_api_key="test"),
        gcs=GCSConfig(bucket="test"),
        firebase=FirebaseConfig(service_account_path="test"),
        google_play=GooglePlayConfig(),
        elevenlabs=ElevenLabsConfig(api_key="test"),
        cloudflare=CloudflareConfig(),
        push_notification=PushNotificationConfig(),
    )

    _validate_config(config)

    # 所有值保持不变
    assert config.app.limits.guest_user_chat_24h_limit == 5
    assert config.app.limits.free_user_chat_24h_limit == 10
    assert config.app.limits.guest_user_voice_24h_limit == 5
    assert config.app.limits.free_user_voice_24h_limit == 10


def test_guest_equals_free_is_valid():
    """测试游客限制等于登录用户是合法的"""
    config = Config(
        app=AppConfig(
            name="test",
            limits=AppConfig.LimitsConfig(
                guest_user_chat_24h_limit=10,
                guest_user_voice_24h_limit=10,
                free_user_chat_24h_limit=10,
                free_user_voice_24h_limit=10,
            ),
        ),
        security=SecurityConfig(secret_key="test"),
        database=DatabaseSettings(),
        google_oauth=GoogleOAuthConfig(),
        verification=VerificationConfig(),
        logging=LoggingConfig(),
        embedding=EmbeddingConfig(),
        agent=AgentConfig(api_key="test", langchain_api_key="test"),
        gcs=GCSConfig(bucket="test"),
        firebase=FirebaseConfig(service_account_path="test"),
        google_play=GooglePlayConfig(),
        elevenlabs=ElevenLabsConfig(api_key="test"),
        cloudflare=CloudflareConfig(),
        push_notification=PushNotificationConfig(),
    )

    _validate_config(config)

    # 允许相等，不应该被修改
    assert config.app.limits.guest_user_chat_24h_limit == 10
    assert config.app.limits.free_user_chat_24h_limit == 10
    assert config.app.limits.guest_user_voice_24h_limit == 10
    assert config.app.limits.free_user_voice_24h_limit == 10


def test_local_only_guest_user_image_gen_limit_in_non_local_environment(config):
    config.app.environment = Environment.DEV
    config.app.limits.test_only_guest_user_image_gen_24h_limit = 5

    with pytest.raises(
        ValueError,
        match="test_only_guest_user_image_gen_24h_limit is only allowed in test environment",
    ):
        _validate_config(config)


def test_local_only_guest_user_image_gen_limit_in_local_environment(config):
    config.app.environment = Environment.TEST
    config.app.limits.test_only_guest_user_image_gen_24h_limit = 5

    # 应该不抛出异常
    _validate_config(config)
    assert config.app.limits.test_only_guest_user_image_gen_24h_limit == 5


def test_local_only_guest_user_image_gen_limit_zero_in_non_local_environment(
    config,
):
    config.app.environment = Environment.PROD
    config.app.limits.test_only_guest_user_image_gen_24h_limit = 0

    # 应该不抛出异常
    _validate_config(config)
    assert config.app.limits.test_only_guest_user_image_gen_24h_limit == 0


def test_agent_config_companion_harness_settings() -> None:
    agent = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        companion_harness={
            "dreaming_idle_seconds": 33,
            "user_feedback_github": {
                "repo": "nascentcore/test",
                "token": "gh_test",
            },
        },
    )

    assert agent.companion_harness.dreaming_idle_seconds == 33
    assert (
        agent.companion_harness.user_feedback_github.repo == "nascentcore/test"
    )
    assert agent.companion_harness.user_feedback_github.token == "gh_test"


def test_companion_harness_dreaming_curator_mode_defaults_to_one_shot() -> None:
    from app.utils.config import DreamingCuratorMode

    agent = AgentConfig(
        api_key="test",
        langchain_api_key="test",
    )
    assert (
        agent.companion_harness.dreaming_curator_mode
        == DreamingCuratorMode.ONE_SHOT
    )


def test_companion_harness_dreaming_curator_mode_sequential_override() -> None:
    from app.utils.config import DreamingCuratorMode

    agent = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        companion_harness={"dreaming_curator_mode": "sequential"},
    )
    assert (
        agent.companion_harness.dreaming_curator_mode
        == DreamingCuratorMode.SEQUENTIAL
    )


def test_companion_harness_inner_tick_monolog_accepts_legacy_maintenance_key() -> (
    None
):
    agent = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        companion_harness={
            "inner_tick": {
                "maintenance": {"min_gap_seconds": 99.0},
            },
        },
    )
    assert agent.companion_harness.inner_tick.monolog.min_gap_seconds == 99.0


def test_companion_harness_config_default_transcript_compaction() -> None:
    agent = AgentConfig(api_key="test", langchain_api_key="test")
    assert agent.companion_harness.transcript.compaction is not None
    assert (
        agent.companion_harness.transcript.compaction
        == DEFAULT_COMPANION_FEATURE_COMPACTION
    )


def test_companion_harness_config_transcript_compaction_null_disables() -> None:
    agent = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        companion_harness={"transcript": {"compaction": None}},
    )
    assert agent.companion_harness.transcript.compaction is None


def test_companion_harness_proactive_chat_base_idle_out_of_range_raises() -> (
    None
):
    with pytest.raises(ValueError, match="base_idle_seconds"):
        AgentConfig(
            api_key="test",
            langchain_api_key="test",
            companion_harness={
                "inner_tick": {"proactive_chat": {"base_idle_seconds": 5.0}}
            },
        )


def test_features_config_uses_pydantic_validation():
    f = FeaturesConfig.model_validate({"unknown_key": "ignored"})
    assert f.experimental_enable_chat_with_user_time_context is True
    assert not hasattr(f, "unknown_key")


def test_companion_transcript_compaction_config_validates():
    AgentConfig(
        api_key="test",
        langchain_api_key="test",
        companion_harness={
            "transcript": {
                "compaction": {
                    "max_context_chars": 12000,
                    "keep_recent_messages": 24,
                    "max_messages_per_episode": 6,
                    "max_episodic_entries": 8,
                    "max_semantic_entries": 8,
                    "summary_max_chars": 800,
                    "retrieval_episode_count": 3,
                    "retrieval_semantic_count": 4,
                    "retrieval_open_loop_count": 3,
                },
                "llm_window_max_messages": 80,
            }
        },
    )


def test_companion_transcript_compaction_invalid_raises():
    with pytest.raises(Exception):
        AgentConfig(
            api_key="test",
            langchain_api_key="test",
            companion_harness={
                "transcript": {"compaction": {"max_context_chars": 50}}
            },
        )


def test_companion_transcript_window_out_of_range_raises():
    with pytest.raises(ValueError, match="window_max_messages"):
        AgentConfig(
            api_key="test",
            langchain_api_key="test",
            companion_harness={"transcript": {"llm_window_max_messages": 1}},
        )


def test_implicit_sign_on_greeting_llm_timeout_out_of_range_raises():
    with pytest.raises(ValueError, match="timeout_sec"):
        AgentConfig(
            api_key="test",
            langchain_api_key="test",
            companion_harness={
                "implicit_sign_on_greeting": {"llm_timeout_sec": 0.5}
            },
        )


def test_implicit_sign_on_greeting_llm_max_attempts_out_of_range_raises():
    with pytest.raises(ValueError, match="max_attempts"):
        AgentConfig(
            api_key="test",
            langchain_api_key="test",
            companion_harness={
                "implicit_sign_on_greeting": {"llm_max_attempts": 6}
            },
        )


def test_proactive_chat_base_idle_seconds_default(config):
    _validate_config(config)
    assert (
        config.agent.companion_harness.inner_tick.proactive_chat.base_idle_seconds
        == 30.0
    )


def test_proactive_chat_base_idle_seconds_out_of_range_raises():
    with pytest.raises(ValueError, match="base_idle_seconds"):
        AgentConfig(
            api_key="test",
            langchain_api_key="test",
            companion_harness={
                "inner_tick": {"proactive_chat": {"base_idle_seconds": 5.0}}
            },
        )


def test_name_for_openrouter_dev_environment():
    """测试DEV环境下的name_for_openrouter属性"""
    app_config = AppConfig(
        name="inty-backend",
        environment=Environment.DEV,
    )

    assert app_config.name_for_openrouter == "https://inty-backend-dev"


def test_name_for_openrouter_prod_environment():
    """测试PROD环境下的name_for_openrouter属性"""
    app_config = AppConfig(
        name="inty-backend",
        environment=Environment.PROD,
    )

    assert app_config.name_for_openrouter == "https://inty-backend-prod"


def test_name_for_openrouter_test_environment():
    """测试TEST环境下的name_for_openrouter属性"""
    app_config = AppConfig(
        name="inty-backend",
        environment=Environment.TEST,
    )

    assert app_config.name_for_openrouter == "https://inty-backend-test"


def test_name_for_openrouter_custom_app_name():
    """测试自定义应用名称的name_for_openrouter属性"""
    app_config = AppConfig(
        name="my-custom-app",
        environment=Environment.DEV,
    )

    assert app_config.name_for_openrouter == "https://my-custom-app-dev"


def test_name_for_openrouter_with_special_characters():
    """测试包含特殊字符的应用名称的name_for_openrouter属性"""
    app_config = AppConfig(
        name="inty-backend-v2",
        environment=Environment.PROD,
    )

    assert app_config.name_for_openrouter == "https://inty-backend-v2-prod"


def test_gemini_live_language_defaults():
    config = GeminiLiveConfig()

    assert config.speech_language_code == "en-US"
    assert config.response_language_name == "English"


def test_gemini_live_config_model_validate_ignores_unknown_keys():
    settings = GeminiLiveConfig.model_validate(
        {
            "enabled": True,
            "project_id": "inty-live-test",
            "unknown_key": "ignored",
        }
    )

    assert settings.enabled is True
    assert settings.project_id == "inty-live-test"
    assert not hasattr(settings, "unknown_key")


def test_chat_messages_window_limit_defaults():
    limits = AppConfig.LimitsConfig()

    assert limits.free_user_chat_messages_limit == 10
    assert limits.sub_user_chat_messages_limit == 1000


def test_app_limits_config_model_validate_ignores_unknown_keys():
    limits = AppConfig.LimitsConfig.model_validate(
        {
            "free_user_chat_24h_limit": 42,
            "guest_user_chat_24h_limit": 7,
            "guest_user_voice_24h_limit": 7,
            "unknown_key": "ignored",
        }
    )

    assert limits.free_user_chat_24h_limit == 42
    assert limits.guest_user_voice_24h_limit == 7
    assert not hasattr(limits, "unknown_key")


def test_database_settings_model_validate_preserves_database_urls():
    settings = DatabaseSettings.model_validate(
        {
            "host": "primary.internal",
            "port": 15432,
            "user": "inty_user",
            "password": "secret",
            "db": "inty_prod",
            "replica_host": "replica.internal",
            "replica_port": 25432,
            "ignored_yaml_key": "ignored",
        }
    )

    assert (
        settings.url
        == "postgresql://inty_user:secret@primary.internal:15432/inty_prod"
    )
    assert (
        settings.async_url
        == "postgresql+asyncpg://inty_user:secret@primary.internal:15432/inty_prod"
    )
    assert (
        settings.async_replica_url
        == "postgresql+asyncpg://inty_user:secret@replica.internal:25432/inty_prod"
    )


def test_google_oauth_config_model_validate_ignores_unknown_keys():
    settings = GoogleOAuthConfig.model_validate(
        {
            "client_id": "google-client",
            "client_secret": "google-secret",
            "redirect_uri": "https://example.com/oauth/google/callback",
            "unknown_key": "ignored",
        }
    )

    assert settings.client_id == "google-client"
    assert settings.client_secret == "google-secret"
    assert settings.redirect_uri == "https://example.com/oauth/google/callback"


def test_verification_config_model_validate_ignores_unknown_keys():
    settings = VerificationConfig.model_validate(
        {
            "code_expire_minutes": 11,
            "unknown_key": "ignored",
        }
    )

    assert settings.code_expire_minutes == 11


def test_api_endpoints_config_model_validate_ignores_unknown_keys():
    settings = APIEndpointsConfig.model_validate(
        {
            "disable_api_v1_chat_completions": True,
            "use_dummy_api_v1_auth_google_login": True,
            "unknown_key": "ignored",
        }
    )

    assert settings.disable_api_v1_chat_completions is True
    assert settings.use_dummy_api_v1_auth_google_login is True


def test_embedding_config_model_validate_ignores_unknown_keys():
    settings = EmbeddingConfig.model_validate(
        {
            "base_url": "https://embedding.example/v1",
            "api_key": "embedding-key",
            "model": "embedding-model",
            "unknown_key": "ignored",
        }
    )

    assert settings.base_url == "https://embedding.example/v1"
    assert settings.api_key == "embedding-key"
    assert settings.model == "embedding-model"


def test_gcs_config_model_validate_ignores_unknown_keys():
    settings = GCSConfig.model_validate(
        {
            "bucket": "inty-test-bucket",
            "use_fake_gcs": True,
            "fake_gcs_base_dir": "/tmp/test-gcs",
            "unknown_key": "ignored",
        }
    )

    assert settings.bucket == "inty-test-bucket"
    assert settings.use_fake_gcs is True
    assert settings.fake_gcs_base_dir == "/tmp/test-gcs"


def test_firebase_config_model_validate_ignores_unknown_keys():
    settings = FirebaseConfig.model_validate(
        {
            "service_account_path": "firebase-test.json",
            "unknown_key": "ignored",
        }
    )

    assert settings.service_account_path == "firebase-test.json"


def test_google_play_config_model_validate_ignores_unknown_keys():
    settings = GooglePlayConfig.model_validate(
        {
            "package_name": "com.example.inty",
            "fallback_tracks": ["production", "beta"],
            "unknown_key": "ignored",
        }
    )

    assert settings.package_name == "com.example.inty"
    assert settings.fallback_tracks == ["production", "beta"]


def test_cloudflare_config_model_validate_ignores_unknown_keys():
    settings = CloudflareConfig.model_validate(
        {
            "domain": "cdn.example.com",
            "enabled": True,
            "fallback_to_original": False,
            "unknown_key": "ignored",
        }
    )

    assert settings.domain == "cdn.example.com"
    assert settings.enabled is True
    assert settings.fallback_to_original is False


def test_elevenlabs_config_model_validate_ignores_unknown_keys():
    settings = ElevenLabsConfig.model_validate(
        {
            "api_key": "eleven-key",
            "model": "eleven_test_model",
            "enabled": False,
            "unknown_key": "ignored",
        }
    )

    assert settings.api_key == "eleven-key"
    assert settings.model == "eleven_test_model"
    assert settings.enabled is False


def test_memory_extraction_config_model_validate_ignores_unknown_keys():
    settings = MemoryExtractionConfig.model_validate(
        {
            "workflow_mode": "daily_incremental_summarization",
            "trigger_new_user_messages": 12,
            "unknown_key": "ignored",
        }
    )

    assert settings.workflow_mode == (
        MemoryExtractionConfig.WorkflowMode.DAILY_INCREMENTAL_SUMMARIZATION
    )
    assert settings.trigger_new_user_messages == 12
    assert not hasattr(settings, "unknown_key")


def test_user_analytics_report_config_model_validate_ignores_unknown_keys():
    settings = UserAnalyticsReportConfig.model_validate(
        {
            "batch_size": 100,
            "statement_timeout_sec": 120,
            "unknown_key": "ignored",
        }
    )

    assert settings.batch_size == 100
    assert settings.statement_timeout_sec == 120


def test_fal_config_model_validate_ignores_unknown_keys():
    settings = FalConfig.model_validate(
        {
            "api_key": "fal-key",
            "unknown_key": "ignored",
        }
    )

    assert settings.api_key == "fal-key"


def test_push_notification_config_model_validate_defaults_stages():
    first = PushNotificationConfig.model_validate({"stages": None})
    second = PushNotificationConfig()

    assert first.stages is not None
    assert second.stages is not None
    first.stages["10min"]["count"] = 99
    assert second.stages["10min"]["count"] == 0


def test_surprise_snap_config_model_validate_defaults_trigger_rounds():
    first = SurpriseSnapConfig.model_validate({"unknown_key": "ignored"})
    second = SurpriseSnapConfig()

    first.trigger_rounds.append(21)
    assert second.trigger_rounds == [3, 8, 15]
    assert not hasattr(first, "unknown_key")


def test_tts_config_model_validate_ignores_unknown_keys():
    settings = TTSConfig.model_validate(
        {
            "use_fake_tts": True,
            "voice_message_narration_mode": "dialogue_and_stage_directions",
            "unknown_key": "ignored",
        }
    )

    assert settings.use_fake_tts is True
    assert (
        settings.voice_message_narration_mode == "dialogue_and_stage_directions"
    )


def test_agent_config_langsmith_always_trace_user_emails_defaults_to_empty_list():
    agent_config = AgentConfig(api_key="test", langchain_api_key="test")

    assert agent_config.langsmith_text_chat_always_trace_user_emails == []


def test_agent_config_langsmith_always_trace_user_emails_supports_explicit_values():
    agent_config = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        langsmith_text_chat_always_trace_user_emails=[
            "dev1@example.com",
            "dev2@example.com",
        ],
    )

    assert agent_config.langsmith_text_chat_always_trace_user_emails == [
        "dev1@example.com",
        "dev2@example.com",
    ]


def test_agent_config_text_to_image_models_accept_none_for_vertex_fallback():
    agent_config = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        free_user_text_to_image_model=None,
        sub_user_text_to_image_model=None,
    )

    assert agent_config.free_user_text_to_image_model is None
    assert agent_config.sub_user_text_to_image_model is None


def test_agent_config_model_validate_ignores_unknown_keys():
    agent_config = AgentConfig.model_validate(
        {
            "api_key": "test",
            "langchain_api_key": "test",
            "free_user_chat_model": "google/gemini-2.5-flash",
            "unknown_key": "ignored",
        }
    )

    assert agent_config.free_user_chat_model == "google/gemini-2.5-flash"
    assert not hasattr(agent_config, "unknown_key")


def test_agent_config_chat_llm_provider_invalid_raises():
    with pytest.raises(ValueError, match="chat_llm_provider"):
        AgentConfig(
            api_key="test",
            langchain_api_key="test",
            chat_llm_provider="bogus",
        )


def test_agent_config_newapi_gemini_bearer_required_when_base_url_set():
    original = os.environ.get("NEWAPI_GEMINI_BEARER_TOKEN")
    try:
        os.environ.pop("NEWAPI_GEMINI_BEARER_TOKEN", None)
        with pytest.raises(ValueError, match="newapi_gemini_bearer_token"):
            AgentConfig(
                api_key="test",
                langchain_api_key="test",
                newapi_gemini_base_url="https://llm.example.com",
            )
    finally:
        if original is None:
            os.environ.pop("NEWAPI_GEMINI_BEARER_TOKEN", None)
        else:
            os.environ["NEWAPI_GEMINI_BEARER_TOKEN"] = original


def test_agent_config_newapi_gemini_accepts_env_bearer_token():
    original = os.environ.get("NEWAPI_GEMINI_BEARER_TOKEN")
    try:
        os.environ["NEWAPI_GEMINI_BEARER_TOKEN"] = "env-bearer"
        agent_config = AgentConfig(
            api_key="test",
            langchain_api_key="test",
            newapi_gemini_base_url="https://llm.example.com",
        )
        assert agent_config.newapi_gemini_bearer_token is None
    finally:
        if original is None:
            os.environ.pop("NEWAPI_GEMINI_BEARER_TOKEN", None)
        else:
            os.environ["NEWAPI_GEMINI_BEARER_TOKEN"] = original


def test_app_config_model_validate_ignores_unknown_keys():
    app_config = AppConfig.model_validate(
        {
            "name": "my-app",
            "environment": "dev",
            "unknown_key": "ignored",
        }
    )

    assert app_config.name == "my-app"
    assert app_config.environment == Environment.DEV
    assert not hasattr(app_config, "unknown_key")


def test_companion_harness_default_user_time_zone_normalizes() -> None:
    agent = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        companion_harness={"default_user_time_zone": "America/Los_Angeles"},
    )
    assert (
        agent.companion_harness.default_user_time_zone == "America/Los_Angeles"
    )


def test_companion_harness_default_user_time_zone_empty_disables() -> None:
    agent = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        companion_harness={"default_user_time_zone": "   "},
    )
    assert agent.companion_harness.default_user_time_zone is None


def test_companion_harness_language_default_none() -> None:
    agent = AgentConfig(api_key="test", langchain_api_key="test")
    assert agent.companion_harness.language is None


def test_companion_harness_language_strips_and_preserves() -> None:
    agent = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        companion_harness={"language": " English "},
    )
    assert agent.companion_harness.language == "English"


def test_companion_harness_language_empty_disables() -> None:
    agent = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        companion_harness={"language": "   "},
    )
    assert agent.companion_harness.language is None


def test_companion_harness_default_user_time_zone_invalid_raises() -> None:
    with pytest.raises(ValueError, match="default_user_time_zone"):
        AgentConfig(
            api_key="test",
            langchain_api_key="test",
            companion_harness={"default_user_time_zone": "America/Not_A_Zone"},
        )


def test_companion_harness_batch_user_messages_mode_default() -> None:
    agent = AgentConfig(api_key="test", langchain_api_key="test")
    assert (
        agent.companion_harness.user_turn.batch_user_messages_llm_call_mode
        == BatchUserMessagesLlmCallMode.MULTI_USER_MESSAGES.value
    )


def test_companion_harness_batch_user_messages_join_mode() -> None:
    agent = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        companion_harness={
            "user_turn": {
                "batch_user_messages_llm_call_mode": (
                    BatchUserMessagesLlmCallMode.JOIN_TO_ONE_USER_MESSAGE.value
                )
            }
        },
    )

    assert (
        agent.companion_harness.user_turn.batch_user_messages_llm_call_mode
        == BatchUserMessagesLlmCallMode.JOIN_TO_ONE_USER_MESSAGE.value
    )


def test_companion_harness_batch_user_messages_invalid_raises() -> None:
    with pytest.raises(ValueError, match="batch_user_messages_llm_call_mode"):
        AgentConfig(
            api_key="test",
            langchain_api_key="test",
            companion_harness={
                "user_turn": {"batch_user_messages_llm_call_mode": "BOGUS"}
            },
        )


def _minimal_yaml_for_load_config(extra_app_content: str = "") -> str:
    return f"""
app:
  name: loadcfg-bootstrap-test
  environment: test
  gcp_service_account_key: ".secrets/inty-backend-key.json"
  features: {{}}
{extra_app_content}security:
  secret_key: "test-secret"
database:
  host: localhost
agent:
  api_key: "test-openrouter"
  langchain_api_key: "test-langchain"
gcs:
  bucket: "test-bucket"
firebase:
  service_account_path: "test-firebase.json"
elevenlabs:
  api_key: "test-eleven"
"""


def _minimal_yaml_for_load_config_harness(extra_companion_harness: str) -> str:
    return f"""
app:
  name: loadcfg-bootstrap-test
  environment: test
  gcp_service_account_key: ".secrets/inty-backend-key.json"
security:
  secret_key: "test-secret"
database:
  host: localhost
agent:
  api_key: "test-openrouter"
  langchain_api_key: "test-langchain"
  companion_harness:
{extra_companion_harness}
gcs:
  bucket: "test-bucket"
firebase:
  service_account_path: "test-firebase.json"
elevenlabs:
  api_key: "test-eleven"
"""


def test_load_config_companion_harness_language() -> None:
    yaml_text = _minimal_yaml_for_load_config_harness(
        "    language: English\n",
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))
    assert cfg.agent.companion_harness.language == "English"


def test_load_config_companion_harness_inner_tick_proactive_chat():
    yaml_text = _minimal_yaml_for_load_config_harness(
        "\n".join(
            [
                "    inner_tick:",
                "      proactive_chat:",
                "        base_idle_seconds: 10",
                "        poll_seconds: 5",
                "",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))
    proactive = cfg.agent.companion_harness.inner_tick.proactive_chat
    assert proactive.base_idle_seconds == 10.0
    assert proactive.poll_seconds == 5.0


def test_load_config_database_settings_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config().replace(
        "database:\n  host: localhost\n",
        "\n".join(
            [
                "database:",
                "  host: primary.internal",
                "  port: 15432",
                "  user: inty_user",
                "  password: secret",
                "  db: inty_prod",
                "  unknown_key: ignored",
                "",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert (
        cfg.database.url
        == "postgresql://inty_user:secret@primary.internal:15432/inty_prod"
    )


def test_load_config_firebase_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config().replace(
        'firebase:\n  service_account_path: "test-firebase.json"\n',
        "\n".join(
            [
                "firebase:",
                "  service_account_path: test-firebase-model.json",
                "  unknown_key: ignored",
                "",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert cfg.firebase.service_account_path == "test-firebase-model.json"


def test_load_config_google_play_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config().replace(
        "elevenlabs:\n",
        "\n".join(
            [
                "google_play:",
                "  package_name: com.example.inty",
                "  fallback_tracks:",
                "    - production",
                "    - beta",
                "  unknown_key: ignored",
                "elevenlabs:\n",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert cfg.google_play.package_name == "com.example.inty"
    assert cfg.google_play.fallback_tracks == ["production", "beta"]


def test_load_config_cloudflare_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config().replace(
        "elevenlabs:\n",
        "\n".join(
            [
                "cloudflare:",
                "  domain: cdn.example.com",
                "  enabled: true",
                "  fallback_to_original: false",
                "  unknown_key: ignored",
                "elevenlabs:\n",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert cfg.cloudflare.domain == "cdn.example.com"
    assert cfg.cloudflare.enabled is True
    assert cfg.cloudflare.fallback_to_original is False


def test_load_config_google_oauth_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config().replace(
        "security:\n",
        "\n".join(
            [
                "google_oauth:",
                "  client_id: google-client",
                "  client_secret: google-secret",
                '  redirect_uri: "https://example.com/oauth/google/callback"',
                "  unknown_key: ignored",
                "security:\n",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert cfg.google_oauth.client_id == "google-client"
    assert cfg.google_oauth.client_secret == "google-secret"
    assert (
        cfg.google_oauth.redirect_uri
        == "https://example.com/oauth/google/callback"
    )


def test_load_config_verification_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config().replace(
        "security:\n",
        "\n".join(
            [
                "verification:",
                "  code_expire_minutes: 13",
                "  unknown_key: ignored",
                "security:\n",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert cfg.verification.code_expire_minutes == 13


def test_load_config_api_endpoints_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config(
        "\n".join(
            [
                "  api_endpoints:",
                "    disable_api_v1_chat_completions: true",
                "    unknown_key: ignored",
                "",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert cfg.app.api_endpoints.disable_api_v1_chat_completions is True


def test_load_config_app_limits_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config(
        "\n".join(
            [
                "  limits:",
                "    guest_user_chat_24h_limit: 3",
                "    guest_user_voice_24h_limit: 3",
                "    unknown_key: ignored",
                "",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert cfg.app.limits.guest_user_chat_24h_limit == 3
    assert cfg.app.limits.guest_user_voice_24h_limit == 3
    assert not hasattr(cfg.app.limits, "unknown_key")


def test_load_config_embedding_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config().replace(
        "agent:\n",
        "\n".join(
            [
                "embedding:",
                "  base_url: https://embedding.example/v1",
                "  api_key: embedding-key",
                "  model: embedding-model",
                "  unknown_key: ignored",
                "agent:\n",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert cfg.embedding.base_url == "https://embedding.example/v1"
    assert cfg.embedding.api_key == "embedding-key"
    assert cfg.embedding.model == "embedding-model"


def test_load_config_gcs_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config().replace(
        'gcs:\n  bucket: "test-bucket"\n',
        "\n".join(
            [
                "gcs:",
                "  bucket: inty-test-bucket",
                "  use_fake_gcs: true",
                "  fake_gcs_base_dir: /tmp/test-gcs",
                "  unknown_key: ignored",
                "",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert cfg.gcs.bucket == "inty-test-bucket"
    assert cfg.gcs.use_fake_gcs is True
    assert cfg.gcs.fake_gcs_base_dir == "/tmp/test-gcs"


def test_load_config_gemini_live_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config().replace(
        "elevenlabs:\n",
        "\n".join(
            [
                "gemini_live:",
                "  enabled: true",
                "  project_id: inty-live-yaml",
                "  unknown_key: ignored",
                "elevenlabs:\n",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert cfg.gemini_live.enabled is True
    assert cfg.gemini_live.project_id == "inty-live-yaml"
    assert not hasattr(cfg.gemini_live, "unknown_key")


def test_load_config_elevenlabs_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config().replace(
        'elevenlabs:\n  api_key: "test-eleven"\n',
        "\n".join(
            [
                "elevenlabs:",
                "  api_key: test-eleven-model",
                "  model: eleven_test_model",
                "  enabled: false",
                "  unknown_key: ignored",
                "",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert cfg.elevenlabs.api_key == "test-eleven-model"
    assert cfg.elevenlabs.model == "eleven_test_model"
    assert cfg.elevenlabs.enabled is False


def test_load_config_memory_extraction_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config().replace(
        "agent:\n",
        "\n".join(
            [
                "memory_extraction:",
                "  workflow_mode: daily_incremental_summarization",
                "  trigger_incremental_messages: 9",
                "  unknown_key: ignored",
                "agent:\n",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert cfg.memory_extraction.workflow_mode == (
        MemoryExtractionConfig.WorkflowMode.DAILY_INCREMENTAL_SUMMARIZATION
    )
    assert cfg.memory_extraction.trigger_incremental_messages == 9
    assert not hasattr(cfg.memory_extraction, "unknown_key")


def test_load_config_push_notification_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config().replace(
        "elevenlabs:\n",
        "\n".join(
            [
                "push_notification:",
                "  batch_size: 25",
                "  stages: null",
                "  unknown_key: ignored",
                "elevenlabs:\n",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert cfg.push_notification.batch_size == 25
    assert cfg.push_notification.stages is not None
    assert cfg.push_notification.stages["10min"] == {"count": 0, "minutes": 10}
    assert not hasattr(cfg.push_notification, "unknown_key")


def test_load_config_user_analytics_report_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config().replace(
        "elevenlabs:\n",
        "\n".join(
            [
                "user_analytics_report:",
                "  batch_size: 100",
                "  statement_timeout_sec: 120",
                "  unknown_key: ignored",
                "elevenlabs:\n",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert cfg.user_analytics_report.batch_size == 100
    assert cfg.user_analytics_report.statement_timeout_sec == 120


def test_load_config_surprise_snap_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config().replace(
        "elevenlabs:\n",
        "\n".join(
            [
                "surprise_snap:",
                '  enabled_since: "2026-05-01T10:00:00Z"',
                "  trigger_rounds:",
                "    - 2",
                "    - 4",
                "  unknown_key: ignored",
                "elevenlabs:\n",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert cfg.surprise_snap.enabled_since == datetime(
        2026, 5, 1, 10, 0, tzinfo=timezone.utc
    )
    assert cfg.surprise_snap.trigger_rounds == [2, 4]
    assert not hasattr(cfg.surprise_snap, "unknown_key")


def test_load_config_fal_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config().replace(
        "elevenlabs:\n",
        "\n".join(
            [
                "fal:",
                "  api_key: fal-yaml-key",
                "  unknown_key: ignored",
                "elevenlabs:\n",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert cfg.fal.api_key == "fal-yaml-key"


def test_load_config_tts_uses_pydantic_validation():
    yaml_text = _minimal_yaml_for_load_config().replace(
        "elevenlabs:\n",
        "\n".join(
            [
                "tts:",
                "  use_fake_tts: true",
                "  voice_message_narration_mode: dialogue_and_stage_directions",
                "  unknown_key: ignored",
                "elevenlabs:\n",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))

    assert cfg.tts.use_fake_tts is True
    assert (
        cfg.tts.voice_message_narration_mode == "dialogue_and_stage_directions"
    )


def test_load_config_weixin_channel_split_multiline_default_false() -> None:
    yaml_text = _minimal_yaml_for_load_config()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))
    assert cfg.weixin_channel.split_multiline_messages is False


def test_load_config_weixin_channel_split_multiline_true() -> None:
    yaml_text = _minimal_yaml_for_load_config().replace(
        "elevenlabs:\n",
        "\n".join(
            [
                "weixin_channel:",
                "  split_multiline_messages: true",
                "elevenlabs:",
                "",
            ]
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))
    assert cfg.weixin_channel.split_multiline_messages is True
