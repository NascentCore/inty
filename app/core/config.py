from typing import Any, Dict, Optional, List, Union

from pydantic_settings import BaseSettings
from pydantic import field_validator, AnyHttpUrl, ValidationInfo


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "InTy"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    
    # 安全配置
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # CORS配置
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # 数据库配置
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: Optional[str] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: ValidationInfo) -> Any:
        if isinstance(v, str):
            return v
        values = info.data
        return f"postgresql://{values['POSTGRES_USER']}:{values['POSTGRES_PASSWORD']}@{values['POSTGRES_SERVER']}/{values['POSTGRES_DB']}"

    # Google OAuth配置
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None
    
    # 验证码配置
    VERIFICATION_CODE_EXPIRE_MINUTES: int = 5  # 验证码有效期（分钟）
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings() 