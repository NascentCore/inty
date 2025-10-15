import pytest

from app.core.config import (
    AgentConfig,
    AppConfig,
    CloudflareConfig,
    Config,
    DatabaseSettings,
    ElevenLabsConfig,
    EmbeddingConfig,
    FirebaseConfig,
    GCSConfig,
    GoogleOAuthConfig,
    GooglePlayConfig,
    LoggingConfig,
    SecurityConfig,
    VerificationConfig,
    _validate_config,
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
    )

    _validate_config(config)

    # 允许相等，不应该被修改
    assert config.app.limits.guest_user_chat_24h_limit == 10
    assert config.app.limits.free_user_chat_24h_limit == 10
    assert config.app.limits.guest_user_voice_24h_limit == 10
    assert config.app.limits.free_user_voice_24h_limit == 10
