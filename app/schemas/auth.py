from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field, model_validator, validator
from pydantic_core import PydanticCustomError

from app.models.user import AuthType, Gender


class Token(BaseModel):
    """认证令牌"""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """令牌载荷"""

    sub: str  # 用户ID
    exp: int  # 过期时间（Unix 时间戳）


class AuthDataBase(BaseModel):
    """认证数据基础模型"""

    pass


class PhoneAuthData(AuthDataBase):
    """手机号认证数据"""

    phone: str
    code: str


class GoogleAuthData(AuthDataBase):
    """Google认证数据"""

    google_token: str  # Google OAuth code


class AuthData(BaseModel):
    """认证数据"""

    phone: Optional[str] = Field(None, pattern=r"^1[3-9]\d{9}$")
    code: Optional[str] = Field(None, min_length=4, max_length=6)
    google_token: Optional[str] = None
    google_id: Optional[str] = None


class UserInfo(BaseModel):
    """用户信息"""

    gender: Gender
    age_group: str
    system_language: str


class RegisterRequest(BaseModel):
    """注册请求"""

    auth_type: AuthType
    auth_data: Dict[str, Any]  # PhoneAuthData 或 GoogleAuthData
    user_info: Optional[UserInfo] = None
    request_id: Optional[str] = None


class LoginRequest(BaseModel):
    """登录请求"""

    phone: str
    code: str
    request_id: Optional[str] = None


class GoogleCallbackRequest(BaseModel):
    """Google回调请求"""

    code: str
    state: str
    request_id: Optional[str] = None


class GuestRequest(BaseModel):
    """游客请求"""

    device_id: Optional[str] = None
    system_language: Optional[str] = None
    age_group: Optional[str] = None
    request_id: Optional[str] = None


class UserCreate(BaseModel):
    """用户创建"""

    auth_type: AuthType
    auth_data: Union[PhoneAuthData, GoogleAuthData]
    user_info: Optional[UserInfo] = None


class GoogleAuthRequest(BaseModel):
    """
    同一端点上的两种互斥登录方式（不要混在同一请求里）：

    - Google 登录：仅 `id_token`（可选 `user_info` / `request_id`）
    - 邮箱密码登录：仅 `email` + `password`（可选 `user_info` / `request_id`）
    """

    id_token: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    user_info: Optional[UserInfo] = None
    request_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_credentials(self):
        """
        验证：必须提供 (仅 id_token) 或 (email+password) 二选一，且
        `id_token` 不得与 `email` / `password` 同现。
        """
        id_token = self.id_token
        email = self.email
        password = self.password

        # Google OAuth 与 email+password 不能混用
        if id_token and (email or password):
            raise PydanticCustomError(
                "incompatible_auth",
                "id_token (Google) cannot be combined with email or password. "
                "Use only id_token, or only email and password together.",
                {},
            )

        # 如果提供了 email，必须同时提供 password
        if email and not password:
            raise PydanticCustomError(
                "missing_password",
                "Password is required when email is provided",
                {"field": "password"},
            )
        # 如果提供了 password，必须同时提供 email
        if password and not email:
            raise PydanticCustomError(
                "missing_email",
                "Email is required when password is provided",
                {"field": "email"},
            )
        # 必须提供 id_token 或 email+password
        if not id_token and not (email and password):
            raise PydanticCustomError(
                "missing_credentials",
                "Either id_token or email+password must be provided",
                {},
            )

        return self


class UserResponse(BaseModel):
    """用户响应"""

    token: str
    user: Dict[str, Any]


class GoogleLoginRequest(BaseModel):
    """Google登录请求"""

    id_token: str
    user_info: Optional[UserInfo] = None
    request_id: Optional[str] = None


class TokenResponse(BaseModel):
    """Token响应"""

    code: int = 200
    message: str = "success"
    data: Dict[str, Any]


class GuestResponse(BaseModel):
    """游客响应"""

    guest_id: str
    token: str
    is_new_guest: bool


class GoogleAuthUrlResponse(BaseModel):
    """Google授权URL响应"""

    code: int = 200
    message: str = "success"
    data: Dict[str, str]


class LoginUserResponse(BaseModel):
    """登录用户响应"""

    id: str
    nickname: str
    avatar: Optional[str] = None
    email: str
    phone: Optional[str] = None
    auth_type: AuthType
    gender: Optional[Gender] = None
    age_group: Optional[str] = None
    system_language: Optional[str] = None
    description: Optional[str] = None
    is_new_user: bool


class LoginResponse(BaseModel):
    """登录响应"""

    token: str
    user: LoginUserResponse
