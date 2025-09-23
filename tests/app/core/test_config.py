import tempfile
from pathlib import Path

import pytest
import yaml

from app.core.config import (
    AgentConfig,
    AppConfig,
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
    load_config,
)


class TestLoggingConfig:
    def test_logging_config_defaults(self):
        """Test LoggingConfig default values"""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert "YYYY-MM-DD HH:mm:ss.SSS" in config.format
        assert config.file == "inty.log"
        assert config.rotation == "100 MB"
        assert config.retention == "7 days"

    def test_logging_config_custom_values(self):
        """Test LoggingConfig with custom values"""
        config = LoggingConfig(
            level="DEBUG",
            format="custom format",
            file="custom.log",
            rotation="50 MB",
            retention="30 days",
        )
        assert config.level == "DEBUG"
        assert config.format == "custom format"
        assert config.file == "custom.log"
        assert config.rotation == "50 MB"
        assert config.retention == "30 days"


class TestSecurityConfig:
    def test_security_config_required_fields(self):
        """Test SecurityConfig with required fields"""
        config = SecurityConfig(secret_key="test-secret")
        assert config.secret_key == "test-secret"
        assert config.algorithm == "HS256"
        assert config.access_token_expire_minutes == 60 * 24 * 7

    def test_security_config_custom_values(self):
        """Test SecurityConfig with custom values"""
        config = SecurityConfig(
            secret_key="custom-secret",
            algorithm="RS256",
            access_token_expire_minutes=1440,
        )
        assert config.secret_key == "custom-secret"
        assert config.algorithm == "RS256"
        assert config.access_token_expire_minutes == 1440


class TestDatabaseSettings:
    def test_database_settings_required_fields(self):
        """Test DatabaseSettings with required fields"""
        config = DatabaseSettings(
            host="localhost",
            port=5432,
            user="testuser",
            password="testpass",
            db="testdb",
        )
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.user == "testuser"
        assert config.password == "testpass"
        assert config.db == "testdb"

    def test_database_settings_defaults(self):
        """Test DatabaseSettings default values"""
        config = DatabaseSettings(
            host="localhost",
            port=5432,
            user="testuser",
            password="testpass",
            db="testdb",
        )
        assert config.pool_size == 50
        assert config.max_overflow == 20
        assert config.pool_timeout == 10
        assert config.pool_recycle == 3600
        assert config.pool_pre_ping is True
        assert config.connect_timeout == 5
        assert config.command_timeout == 30

    def test_database_url_property(self):
        """Test DatabaseSettings url property"""
        config = DatabaseSettings(
            host="localhost",
            port=5432,
            user="testuser",
            password="testpass",
            db="testdb",
        )
        expected_url = "postgresql://testuser:testpass@localhost:5432/testdb"
        assert config.url == expected_url

    def test_database_async_url_property(self):
        """Test DatabaseSettings async_url property"""
        config = DatabaseSettings(
            host="localhost",
            port=5432,
            user="testuser",
            password="testpass",
            db="testdb",
        )
        expected_url = "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"
        assert config.async_url == expected_url


class TestGoogleOAuthConfig:
    def test_google_oauth_config_defaults(self):
        """Test GoogleOAuthConfig default values"""
        config = GoogleOAuthConfig()
        assert config.client_id is None
        assert config.client_secret is None
        assert config.redirect_uri is None

    def test_google_oauth_config_custom_values(self):
        """Test GoogleOAuthConfig with custom values"""
        config = GoogleOAuthConfig(
            client_id="test-client-id",
            client_secret="test-client-secret",
            redirect_uri="http://localhost:8000/callback",
        )
        assert config.client_id == "test-client-id"
        assert config.client_secret == "test-client-secret"
        assert config.redirect_uri == "http://localhost:8000/callback"


class TestVerificationConfig:
    def test_verification_config_defaults(self):
        """Test VerificationConfig default values"""
        config = VerificationConfig()
        assert config.code_expire_minutes == 5

    def test_verification_config_custom_values(self):
        """Test VerificationConfig with custom values"""
        config = VerificationConfig(code_expire_minutes=10)
        assert config.code_expire_minutes == 10


class TestAppConfig:
    def test_app_config_defaults(self):
        """Test AppConfig default values"""
        config = AppConfig()
        assert config.name == "inty-backend"
        assert config.debug is False
        assert config.debug_messages is True
        assert config.api_v1_prefix == "/api/v1"
        assert config.backend_cors_origins is None
        assert config.limits.free_user_image_gen_daily_limit == 4
        assert config.limits.free_user_chat_total_limit == 100


class TestAgentConfig:
    def test_agent_config_custom_values(self):
        """Test AgentConfig with custom values"""
        config = AgentConfig(
            model="custom-model",
            base_url="https://custom-api.com",
            api_key="custom-api-key",
            langchain_api_key="custom-langchain-api-key",
            temperature=0.8,
            max_tokens=2000,
            enable_debug_logging=True,
        )
        assert config.model == "custom-model"
        assert config.base_url == "https://custom-api.com"
        assert config.api_key == "custom-api-key"
        assert config.temperature == 0.8
        assert config.max_tokens == 2000
        assert config.enable_debug_logging is True

class TestFirebaseConfig:
    def test_firebase_config_required_fields(self):
        """Test FirebaseConfig with required fields"""
        config = FirebaseConfig(service_account_path="path/to/firebase-key.json")
        assert config.service_account_path == "path/to/firebase-key.json"


class TestGooglePlayConfig:

    def test_google_play_config_defaults(self):
        """Test GooglePlayConfig default values"""
        config = GooglePlayConfig(package_name="com.test.app")
        assert config.webhook_secret is None
        assert config.enable_version_check is True
        assert config.min_supported_version == 1
        assert config.release_track == "production"
        assert config.fallback_tracks == ["production", "internal"]

    def test_google_play_config_custom_values(self):
        """Test GooglePlayConfig with custom values"""
        config = GooglePlayConfig(
            package_name="com.custom.app",
            webhook_secret="custom-secret",
            enable_version_check=False,
            min_supported_version=2,
            release_track="internal",
        )
        assert config.webhook_secret == "custom-secret"
        assert config.enable_version_check is False
        assert config.min_supported_version == 2
        assert config.release_track == "internal"


class TestElevenLabsConfig:
    def test_elevenlabs_config_defaults(self):
        """Test ElevenLabsConfig default values"""
        config = ElevenLabsConfig(api_key="test-api-key")
        assert config.api_key == "test-api-key"
        assert config.model == "eleven_multilingual_v2"
        assert config.voice_id == "JBFqnCBsd6RMkjVDRZzb"
        assert config.output_format == "mp3_44100_128"
        assert config.enabled is True
        assert config.max_text_length == 5000

    def test_elevenlabs_config_custom_values(self):
        """Test ElevenLabsConfig with custom values"""
        config = ElevenLabsConfig(
            api_key="custom-api-key",
            model="custom-model",
            voice_id="custom-voice-id",
            output_format="mp3_22050_32",
            enabled=False,
            max_text_length=3000,
        )
        assert config.api_key == "custom-api-key"
        assert config.model == "custom-model"
        assert config.voice_id == "custom-voice-id"
        assert config.output_format == "mp3_22050_32"
        assert config.enabled is False
        assert config.max_text_length == 3000


class TestLoadConfig:
    def test_load_config_success(self):
        """Test successful config loading"""
        test_config_data = {
            "app": {
                "name": "TestApp",
                "debug": False,
                "backend_cors_origins": ["http://localhost:3000"],
                "limits": {
                    "free_user_image_gen_daily_limit": 4,
                    "free_user_chat_total_limit": 100,
                },
            },
            "agent": {
                "api_key": "test-api-key",
                "langchain_api_key": "test-langchain-api-key",
            },
            "security": {"secret_key": "test-secret"},
            "database": {
                "host": "localhost",
                "port": 5432,
                "user": "testuser",
                "password": "testpass",
                "db": "testdb",
            },
            "google_oauth": {},
            "verification": {},
            "logging": {"level": "DEBUG"},
            "gcs": {"bucket": "test-bucket", "credentials": "test-credentials"},
            "firebase": {"service_account_path": "test-path"},
            "google_play": {
                "service_account_key": "test-key",
                "package_name": "com.test.app",
            },
            "elevenlabs": {"api_key": "test-key"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config_data, f)
            temp_config_path = f.name

        try:
            config = load_config(temp_config_path)
            assert config.app.name == "TestApp"
            assert config.app.debug is False
            assert config.app.backend_cors_origins == ["http://localhost:3000"]
            assert config.app.limits.free_user_image_gen_daily_limit == 4
            assert config.app.limits.free_user_chat_total_limit == 100
            assert config.security.secret_key == "test-secret"
            assert config.database.host == "localhost"
            assert config.database.port == 5432
            assert config.database.user == "testuser"
            assert config.database.password == "testpass"
            assert config.database.db == "testdb"
            assert config.logging.level == "DEBUG"
            assert config.gcs.bucket == "test-bucket"
            assert config.firebase.service_account_path == "test-path"
            assert config.google_play.package_name == "com.test.app"
            assert config.elevenlabs.api_key == "test-key"
        finally:
            Path(temp_config_path).unlink()

    def test_load_config_file_not_found(self):
        """Test config loading with non-existent file"""
        with pytest.raises(SystemExit):
            load_config("non_existent_config.yaml")
