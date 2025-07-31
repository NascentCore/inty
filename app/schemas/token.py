from typing import Optional

from pydantic import BaseModel


class Token(BaseModel):
    """Token Schema"""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Token Payload Schema"""

    sub: Optional[str] = None  # 用户ID
    exp: Optional[int] = None  # 过期时间
