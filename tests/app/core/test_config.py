import tempfile
import yaml
from pathlib import Path
import pytest

from app.core.config import (
    LoggingConfig,
    SecurityConfig,
    DatabaseSettings,
    GoogleOAuthConfig,
    VerificationConfig,
    AppConfig,
    EmbeddingConfig,
    AgentConfig,
    GCSConfig,
    FirebaseConfig,
    GooglePlayConfig,
    ElevenLabsConfig,
    Config,
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
        assert config.debug is True
        assert config.debug_messages is True
        assert config.api_v1_prefix == "/api/v1"
        assert config.backend_cors_origins == ["http://localhost:3000"]
        assert config.limits.free_user_image_gen_daily_limit == 4
        assert config.limits.free_user_chat_total_limit == 100

    def test_app_config_custom_values(self):
        """Test AppConfig with custom values"""
        cors_origins = ["http://localhost:3000", "http://localhost:8000"]
        config = AppConfig(
            name="CustomApp",
            debug=False,
            debug_messages=False,
            api_v1_prefix="/api/v2",
            backend_cors_origins=cors_origins,
        )
        assert config.name == "CustomApp"
        assert config.debug is False
        assert config.debug_messages is False
        assert config.api_v1_prefix == "/api/v2"
        assert config.backend_cors_origins == cors_origins

    def test_app_config_default_cors_origins(self):
        """Test AppConfig default backend_cors_origins"""
        config = AppConfig()
        assert config.backend_cors_origins == ["http://localhost:3000"]


class TestEmbeddingConfig:
    def test_embedding_config_defaults(self):
        """Test EmbeddingConfig default values"""
        config = EmbeddingConfig()
        assert config.base_url == "http://localhost:8001/v1"
        assert config.api_key == "sk-proj-1234567890"
        assert config.model == "DMetaSoul/Dmeta-embedding-zh-small"

    def test_embedding_config_custom_values(self):
        """Test EmbeddingConfig with custom values"""
        config = EmbeddingConfig(
            base_url="https://custom-api.com/v1",
            api_key="custom-api-key",
            model="custom-model",
        )
        assert config.base_url == "https://custom-api.com/v1"
        assert config.api_key == "custom-api-key"
        assert config.model == "custom-model"





class TestAgentConfig:
    def test_agent_config_defaults(self):
        """Test AgentConfig default values"""
        config = AgentConfig()
        assert config.model == "google/gemini-2.5-flash"
        assert config.base_url == "https://openrouter.ai/api/v1"
        assert config.api_key == "<fill-in-config.yaml>"
        assert config.temperature == 0.5
        assert config.max_tokens == 1000
        assert config.top_p == 1.0
        assert config.top_k == 50
        assert config.frequency_penalty == 0.0
        assert config.presence_penalty == 0.0
        assert config.enable_debug_logging is False
        assert config.vertex_image_model == "imagen-4.0-fast-generate-preview-06-06"

    def test_agent_config_custom_values(self):
        """Test AgentConfig with custom values"""
        config = AgentConfig(
            model="custom-model",
            base_url="https://custom-api.com",
            api_key="custom-api-key",
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


class TestGCSConfig:
    def test_gcs_config_required_fields(self):
        """Test GCSConfig with required fields"""
        config = GCSConfig(bucket="test-bucket", credentials="path/to/credentials.json")
        assert config.bucket == "test-bucket"
        assert config.credentials == "path/to/credentials.json"


class TestFirebaseConfig:
    def test_firebase_config_required_fields(self):
        """Test FirebaseConfig with required fields"""
        config = FirebaseConfig(service_account_path="path/to/firebase-key.json")
        assert config.service_account_path == "path/to/firebase-key.json"


class TestGooglePlayConfig:
    def test_google_play_config_required_fields(self):
        """Test GooglePlayConfig with required fields"""
        config = GooglePlayConfig(
            service_account_key="service-account-key", package_name="com.test.app"
        )
        assert config.service_account_key == "service-account-key"
        assert config.package_name == "com.test.app"

    def test_google_play_config_defaults(self):
        """Test GooglePlayConfig default values"""
        config = GooglePlayConfig(
            service_account_key="service-account-key", package_name="com.test.app"
        )
        assert config.webhook_secret is None
        assert config.enable_version_check is True
        assert config.min_supported_version == 1
        assert config.release_track == "production"
        assert config.fallback_tracks == ["production", "internal"]

    def test_google_play_config_custom_values(self):
        """Test GooglePlayConfig with custom values"""
        config = GooglePlayConfig(
            service_account_key="custom-key",
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

    def test_google_play_config_default_fallback_tracks(self):
        """Test GooglePlayConfig default fallback_tracks"""
        config = GooglePlayConfig(
            service_account_key="service-account-key", package_name="com.test.app"
        )
        assert config.fallback_tracks == ["production", "internal"]


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


class TestConfig:
    def test_config_creation(self):
        """Test Config creation with all required components"""
        app_config = AppConfig()
        security_config = SecurityConfig(secret_key="test-secret")
        database_config = DatabaseSettings(
            host="localhost", port=5432, user="test", password="test", db="test"
        )
        google_oauth_config = GoogleOAuthConfig()
        verification_config = VerificationConfig()
        logging_config = LoggingConfig()
        embedding_config = EmbeddingConfig()
        agent_config = AgentConfig()
        gcs_config = GCSConfig(bucket="test", credentials="test")
        firebase_config = FirebaseConfig(service_account_path="test")
        google_play_config = GooglePlayConfig(
            service_account_key="test", package_name="com.test.app"
        )
        elevenlabs_config = ElevenLabsConfig(api_key="test")

        config = Config(
            app=app_config,
            security=security_config,
            database=database_config,
            google_oauth=google_oauth_config,
            verification=verification_config,
            logging=logging_config,
            embedding=embedding_config,
            agent=agent_config,
            gcs=gcs_config,
            firebase=firebase_config,
            google_play=google_play_config,
            elevenlabs=elevenlabs_config,
        )

        assert config.app == app_config
        assert config.security == security_config
        assert config.database == database_config
        assert config.google_oauth == google_oauth_config
        assert config.verification == verification_config
        assert config.logging == logging_config
        assert config.embedding == embedding_config
        assert config.agent == agent_config
        assert config.gcs == gcs_config
        assert config.firebase == firebase_config
        assert config.google_play == google_play_config
        assert config.elevenlabs == elevenlabs_config


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
            "embedding": {},
            "agent": {},
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
            assert config.gcs.credentials == "test-credentials"
            assert config.firebase.service_account_path == "test-path"
            assert config.google_play.service_account_key == "test-key"
            assert config.google_play.package_name == "com.test.app"
            assert config.elevenlabs.api_key == "test-key"
        finally:
            Path(temp_config_path).unlink()

    def test_load_config_file_not_found(self):
        """Test config loading with non-existent file"""
        with pytest.raises(SystemExit):
            load_config("non_existent_config.yaml")

    def test_load_config_with_missing_sections(self):
        """Test config loading with missing sections (should use defaults)"""
        test_config_data = {
            "security": {"secret_key": "test-secret"},
            "database": {
                "host": "localhost",
                "port": 5432,
                "user": "testuser",
                "password": "testpass",
                "db": "testdb",
            },
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
            # Should use defaults for missing sections
            assert config.app.name == "inty-backend"
            assert config.app.debug is True
            assert config.logging.level == "INFO"
            assert config.verification.code_expire_minutes == 5
        finally:
            Path(temp_config_path).unlink()
