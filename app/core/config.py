from typing import Any, Dict, Optional, List, Union
from dataclasses import dataclass
from pathlib import Path
import yaml
import sys
from pydantic import AnyHttpUrl

@dataclass
class LoggingConfig:
    level: str
    format: str
    file: str
    rotation: str
    retention: str

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
    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30
    pool_recycle: int = 1800
    pool_pre_ping: bool = True

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
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: List[AnyHttpUrl] = None

    def __post_init__(self):
        if self.backend_cors_origins is None:
            self.backend_cors_origins = []

@dataclass
class EmbeddingConfig:
    base_url: str = "http://localhost:8001/v1"
    api_key: str = "sk-proj-1234567890"
    model: str = "DMetaSoul/Dmeta-embedding-zh-small"


class AgentConfig:
    model: str = "ep-20250210154211-js9rc"
    base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    api_key: str = "ff9ed2dd-cdf0-40d4-b4ec-d3aa19e2bd0b"
    temperature: float = 0.5
    max_tokens: int = 1000

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

def load_config(path: str = "config.yaml") -> Config:
    config_path = Path(path)
    if not config_path.exists():
        print(f"config file {path} not found!")
        sys.exit(1)
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return Config(
        app=AppConfig(**data.get("app", {})),
        security=SecurityConfig(**data.get("security", {})),
        database=DatabaseSettings(**data.get("database", {})),
        google_oauth=GoogleOAuthConfig(**data.get("google_oauth", {})),
        verification=VerificationConfig(**data.get("verification", {})),
        logging=LoggingConfig(**data.get("logging", {})),
        embedding=EmbeddingConfig(**data.get("embedding", {})),
        agent=AgentConfig(**data.get("agent", {}))
    )

# load config
settings = load_config() 