from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VerificationCodeBase(BaseModel):
    """验证码基础模型"""

    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    code: str = Field(..., min_length=4, max_length=6)
    purpose: str = Field(..., pattern="^(REGISTER|LOGIN|RESET_PASSWORD)$")


class VerificationCodeCreate(VerificationCodeBase):
    """创建验证码"""

    request_id: Optional[str] = None


class VerificationCodeInDB(VerificationCodeBase):
    """数据库中的验证码"""

    id: str
    created_at: datetime
    expires_at: datetime
    is_used: bool = False

    class Config:
        from_attributes = True


class VerificationCodeVerify(BaseModel):
    """验证验证码"""

    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    code: str = Field(..., min_length=4, max_length=6)
    request_id: Optional[str] = None
