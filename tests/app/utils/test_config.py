import tempfile
from pathlib import Path

import pytest

from app.utils.companion_feature_defaults import (
    DEFAULT_COMPANION_FEATURE_COMPACTION,
)
from app.utils.config import (
    AgentConfig,
    AppConfig,
    CompanionMemoryBootstrapType,
    FeaturesConfig,
    CloudflareConfig,
    Config,
    DatabaseSettings,
    ElevenLabsConfig,
    EmbeddingConfig,
    Environment,
    FirebaseConfig,
    GCSConfig,
    GeminiLiveConfig,
    GoogleOAuthConfig,
    GooglePlayConfig,
    LoggingConfig,
    PushNotificationConfig,
    SecurityConfig,
    VerificationConfig,
    _validate_config,
    load_config,
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


def test_local_only_guest_user_image_gen_limit_zero_in_non_local_environment(config):
    config.app.environment = Environment.PROD
    config.app.limits.test_only_guest_user_image_gen_24h_limit = 0

    # 应该不抛出异常
    _validate_config(config)
    assert config.app.limits.test_only_guest_user_image_gen_24h_limit == 0


def test_features_config_default_companion_transcript_compaction():
    f = FeaturesConfig()
    assert f.companion_transcript_compaction is not None
    assert f.companion_transcript_compaction == DEFAULT_COMPANION_FEATURE_COMPACTION


def test_features_config_companion_transcript_compaction_null_disables():
    f = FeaturesConfig(companion_transcript_compaction=None)
    assert f.companion_transcript_compaction is None


def test_companion_transcript_compaction_config_validates(config):
    config.app.features = FeaturesConfig(
        companion_transcript_compaction={
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
        companion_transcript_llm_window_max_messages=80,
    )
    _validate_config(config)


def test_companion_transcript_compaction_invalid_raises(config):
    config.app.features = FeaturesConfig(
        companion_transcript_compaction={"max_context_chars": 50},
    )
    with pytest.raises(ValueError):
        _validate_config(config)


def test_companion_transcript_window_out_of_range_raises(config):
    config.app.features = FeaturesConfig(companion_transcript_llm_window_max_messages=1)
    with pytest.raises(ValueError):
        _validate_config(config)


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


def test_chat_messages_window_limit_defaults():
    limits = AppConfig.LimitsConfig()

    assert limits.free_user_chat_messages_limit == 10
    assert limits.sub_user_chat_messages_limit == 1000


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


def test_features_config_companion_memory_bootstrap_type_default():
    f = FeaturesConfig()
    assert f.companion_memory_bootstrap_type == (
        CompanionMemoryBootstrapType.USER_INTERACTIVE.value
    )


def test_features_config_companion_memory_bootstrap_type_normalizes_case():
    f = FeaturesConfig(companion_memory_bootstrap_type="user_interactive")
    assert f.companion_memory_bootstrap_type == (
        CompanionMemoryBootstrapType.USER_INTERACTIVE.value
    )


def test_features_config_companion_memory_bootstrap_type_invalid_raises():
    with pytest.raises(ValueError, match="companion_memory_bootstrap_type"):
        FeaturesConfig(companion_memory_bootstrap_type="BOGUS")


def _minimal_yaml_for_load_config(extra_features: str) -> str:
    return f"""
app:
  name: loadcfg-bootstrap-test
  environment: test
  gcp_service_account_key: ".secrets/inty-backend-key.json"
  features:
{extra_features}
security:
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


def test_load_config_explicit_companion_memory_bootstrap_type():
    yaml_text = _minimal_yaml_for_load_config(
        "    companion_memory_bootstrap_type: USER_INTERACTIVE\n",
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        cfg = load_config(str(path))
    assert cfg.app.features.companion_memory_bootstrap_type == (
        CompanionMemoryBootstrapType.USER_INTERACTIVE.value
    )
