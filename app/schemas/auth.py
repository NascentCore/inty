from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

from app.models.user import Gender, AuthType


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
    phone: Optional[str] = Field(None, pattern=r'^1[3-9]\d{9}$')
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


class LoginRequest(BaseModel):
    """登录请求"""
    phone: str
    code: str


class GoogleCallbackRequest(BaseModel):
    """Google回调请求"""
    code: str
    state: str


class GuestRequest(BaseModel):
    """游客请求"""
    device_id: Optional[str] = None
    system_language: Optional[str] = None


class UserCreate(BaseModel):
    """用户创建"""
    auth_type: AuthType
    auth_data: Union[PhoneAuthData, GoogleAuthData]
    user_info: Optional[UserInfo] = None


class GoogleAuthRequest(BaseModel):
    """Google认证请求"""
    id_token: str
    user_info: Optional[UserInfo] = None


class UserResponse(BaseModel):
    """用户响应"""
    token: str
    user: Dict[str, Any]


class GoogleLoginRequest(BaseModel):
    """Google登录请求"""
    id_token: str
    user_info: Optional[UserInfo] = None


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
    avatar: str
    email: str
    phone: Optional[str] = None
    auth_type: AuthType
    is_new_user: bool


class LoginResponse(BaseModel):
    """登录响应"""
    token: str
    user: LoginUserResponse