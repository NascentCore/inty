import pytest

from app.core.config import (
    AgentConfig,
    AppConfig,
    CloudflareConfig,
    Config,
    DatabaseSettings,
    ElevenLabsConfig,
    EmbeddingConfig,
    Environment,
    FirebaseConfig,
    GCSConfig,
    GoogleOAuthConfig,
    GooglePlayConfig,
    LoggingConfig,
    SecurityConfig,
    VerificationConfig,
    _validate_config,
)


@pytest.fixture
def config():
    return Config(
        app=AppConfig(
            name="test",
            environment=Environment.PROD,  # 非local环境
            limits=AppConfig.LimitsConfig(
                local_only_guest_user_image_gen_24h_limit=0,  # 合法配置
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


def test_local_only_guest_user_image_gen_limit_in_non_local_environment(config):
    config.app.environment = Environment.DEV
    config.app.limits.local_only_guest_user_image_gen_24h_limit = 5

    with pytest.raises(
        ValueError,
        match="local_only_guest_user_image_gen_24h_limit is only allowed in local environment",
    ):
        _validate_config(config)


def test_local_only_guest_user_image_gen_limit_in_local_environment(config):
    config.app.environment = Environment.TEST
    config.app.limits.local_only_guest_user_image_gen_24h_limit = 5

    # 应该不抛出异常
    _validate_config(config)
    assert config.app.limits.local_only_guest_user_image_gen_24h_limit == 5


def test_local_only_guest_user_image_gen_limit_zero_in_non_local_environment(config):
    config.app.environment = Environment.PROD
    config.app.limits.local_only_guest_user_image_gen_24h_limit = 0

    # 应该不抛出异常
    _validate_config(config)
    assert config.app.limits.local_only_guest_user_image_gen_24h_limit == 0


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


def test_name_for_openrouter_local_environment():
    """测试LOCAL环境下的name_for_openrouter属性"""
    app_config = AppConfig(
        name="inty-backend",
        environment=Environment.TEST,
    )

    assert app_config.name_for_openrouter == "https://inty-backend-local"


def test_name_for_openrouter_unspecified_environment():
    """测试UNSPECIFIED环境下的name_for_openrouter属性"""
    app_config = AppConfig(
        name="inty-backend",
        environment=Environment.UNSPECIFIED,
    )

    assert app_config.name_for_openrouter == "https://inty-backend-unspecified"


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
