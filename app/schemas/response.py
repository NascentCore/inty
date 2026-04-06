"""API 响应外壳与业务错误定义。

HTTP 状态码 / body.code / data.error_code 使用规则（与 Kotlin 端
android_app/core/data/.../BusinessErrorCodes.kt 及 NetServiceMgr 保持一致）：

- **HTTP status（HTTP 状态码）**：仅用于请求或基础设施失败。4xx（如 400 错误请求、
  404 未找到）或 5xx（服务端错误）。后端抛出 HTTPException 时，客户端收到该状态码及
  通常为 FastAPI 风格 body（如 {"detail": "..."}）。不要用 HTTP 状态码表示业务结果
  （如需要订阅），应通过响应 body 表示。

- **Body code（APIResponse.code）**：成功 = 200。业务错误 = 数字码（如 10001001 表示
  SUBSCRIPTION_REQUIRED）。使用 APIResponse.success() 或 APIResponse.error(...) 的
  响应通常以 HTTP 200 返回；客户端必须读取 body，并根据 body.code（以及存在时的
  data.error_code）分支处理。

- **data.error_code**：当 body.code != 200 时，data 可能包含字符串 "error_code"
  （如 "SUBSCRIPTION_REQUIRED"）及可选的 "description" 等字段（如限额类错误中的
  used_count、daily_limit）。用 data.error_code 做业务错误类型分支；用 body.code
  做数字匹配，body.message 做展示。
"""

from enum import StrEnum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class MatchedAgentImageItem(BaseModel):
    """One ranked image from text_match_image_description recommend sort."""

    agent_id: str = Field(..., description="Agent that owns this image")
    image_url: str = Field(
        ...,
        description="Image URL for clients (CDN proxy when Cloudflare is enabled, else original)",
    )
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Fuzzy similarity score vs query text, higher is closer match",
    )
    image_description: Optional[str] = Field(
        None,
        description="Stored description: resource generation_prompt or exclusive caption",
    )


class PaginationData(BaseModel, Generic[T]):
    """分页数据结构"""

    list: List[T] = []  # 数据列表
    total: int = 0  # 总记录数
    page: int = 1  # 当前页码
    page_size: int = 10  # 每页数量
    total_pages: int = 0  # 总页数
    matched_image_items: Optional[List[MatchedAgentImageItem]] = Field(
        None,
        description=(
            "When sort=text_match_image_description: ranked image hits for this page; "
            "`list` holds distinct agents referenced by these items in order of first appearance."
        ),
    )


class PagedResponse(BaseModel, Generic[T]):
    """分页数据结构"""

    items: List[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 0


class APIResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: Optional[T] = None

    @classmethod
    def success(
        cls, data: Optional[T] = None, message: str = "success"
    ) -> "APIResponse[T]":
        return cls(code=200, message=message, data=data)

    @classmethod
    def error(
        cls, message: str, code: int = 400, data: Optional[T] = None
    ) -> "APIResponse[T]":
        return cls(code=code, message=message, data=data)


class APIErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None
    request_id: str


class PaginationResponse(APIResponse[PaginationData]):
    """分页响应"""

    pass


class BizError(BaseModel):
    """业务错误信息模型"""

    code: int  # HTTP 状态码
    error_code: str  # 业务错误码
    message: str  # 业务错误消息


class UsageLimitExceeded(BizError):
    # 用来进一步解释错误信息的详细信息
    used_count: int
    daily_limit: int


# TODO：需要与前端确认错误码和错误消息是否一致，使用 enum 方便 Stainless SDK 自动生成错误码和错误消息
# 代码仍在开发中，目前无效
class BusinessErrorCodeEnum(StrEnum):
    """业务错误码枚举类型，用于返回错误信息给前端"""

    SUBSCRIPTION_REQUIRED = "SUBSCRIPTION_REQUIRED"
    IMAGE_GENERATION_LIMIT_REACHED = "IMAGE_GENERATION_LIMIT_REACHED"
    AGENT_CREATION_LIMIT_REACHED = "AGENT_CREATION_LIMIT_REACHED"
    VOICE_GENERATION_LIMIT_REACHED = "VOICE_GENERATION_LIMIT_REACHED"
    MUSIC_GENERATION_LIMIT_REACHED = "MUSIC_GENERATION_LIMIT_REACHED"
    GUEST_LOGIN_REQUIRED = "GUEST_LOGIN_REQUIRED"
    IMAGE_GENERATION_BLOCKED = "IMAGE_GENERATION_BLOCKED"
    LIVE_CHAT_AGENT_LIMIT_REACHED = "LIVE_CHAT_AGENT_LIMIT_REACHED"
    LIVE_CHAT_DURATION_LIMIT_REACHED = "LIVE_CHAT_DURATION_LIMIT_REACHED"

    @property
    def code(self) -> int:
        """返回对应的数字错误码"""
        error_code_map = {
            BusinessErrorCodeEnum.SUBSCRIPTION_REQUIRED: 10001001,
            BusinessErrorCodeEnum.IMAGE_GENERATION_LIMIT_REACHED: 10001002,
            BusinessErrorCodeEnum.AGENT_CREATION_LIMIT_REACHED: 10001003,
            BusinessErrorCodeEnum.VOICE_GENERATION_LIMIT_REACHED: 10001004,
            BusinessErrorCodeEnum.MUSIC_GENERATION_LIMIT_REACHED: 10001009,
            BusinessErrorCodeEnum.GUEST_LOGIN_REQUIRED: 10001005,
            BusinessErrorCodeEnum.IMAGE_GENERATION_BLOCKED: 10001006,
            BusinessErrorCodeEnum.LIVE_CHAT_AGENT_LIMIT_REACHED: 10001007,
            BusinessErrorCodeEnum.LIVE_CHAT_DURATION_LIMIT_REACHED: 10001008,
        }
        return error_code_map[self]

    @property
    def message(self) -> str:
        """返回对应的错误消息"""
        error_message_map = {
            BusinessErrorCodeEnum.SUBSCRIPTION_REQUIRED: "Subscription required",
            BusinessErrorCodeEnum.IMAGE_GENERATION_LIMIT_REACHED: "Image generation limit reached",
            BusinessErrorCodeEnum.AGENT_CREATION_LIMIT_REACHED: "Character creation limit reached",
            BusinessErrorCodeEnum.VOICE_GENERATION_LIMIT_REACHED: "Voice generation limit reached",
            BusinessErrorCodeEnum.MUSIC_GENERATION_LIMIT_REACHED: "Music generation limit reached",
            BusinessErrorCodeEnum.GUEST_LOGIN_REQUIRED: "Guest login required - Please sign in with Google",
            BusinessErrorCodeEnum.IMAGE_GENERATION_BLOCKED: "Image generation was blocked by safety filter",
            BusinessErrorCodeEnum.LIVE_CHAT_AGENT_LIMIT_REACHED: "Live chat agent limit reached",
            BusinessErrorCodeEnum.LIVE_CHAT_DURATION_LIMIT_REACHED: "Live chat duration limit reached",
        }
        return error_message_map[self]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，兼容现有的 BusinessErrorCode 格式"""
        return {
            "code": self.code,
            "error_code": self.value,
            "message": self.message,
        }


# 业务错误码定义
class BusinessErrorCode:
    SUBSCRIPTION_REQUIRED = {
        "code": 10001001,
        "error_code": "SUBSCRIPTION_REQUIRED",
        "message": "Subscription required",
    }
    IMAGE_GENERATION_LIMIT_REACHED = {
        "code": 10001002,
        "error_code": "IMAGE_GENERATION_LIMIT_REACHED",
        "message": "Image generation limit reached",
    }
    AGENT_CREATION_LIMIT_REACHED = {
        "code": 10001003,
        "error_code": "AGENT_CREATION_LIMIT_REACHED",
        "message": "Character creation limit reached",
    }
    VOICE_GENERATION_LIMIT_REACHED = {
        "code": 10001004,
        "error_code": "VOICE_GENERATION_LIMIT_REACHED",
        "message": "Voice generation limit reached",
    }
    MUSIC_GENERATION_LIMIT_REACHED = {
        "code": 10001009,
        "error_code": "MUSIC_GENERATION_LIMIT_REACHED",
        "message": "Music generation limit reached",
    }
    GUEST_LOGIN_REQUIRED = {
        "code": 10001005,
        "error_code": "GUEST_LOGIN_REQUIRED",
        "message": "Guest login required - Please sign in with Google",
    }
    IMAGE_GENERATION_BLOCKED = {
        "code": 10001006,
        "error_code": "IMAGE_GENERATION_BLOCKED",
        "message": "Image generation was blocked by safety filter",
    }
    LIVE_CHAT_AGENT_LIMIT_REACHED = {
        "code": 10001007,
        "error_code": "LIVE_CHAT_AGENT_LIMIT_REACHED",
        "message": "Live chat agent limit reached",
    }
    LIVE_CHAT_DURATION_LIMIT_REACHED = {
        "code": 10001008,
        "error_code": "LIVE_CHAT_DURATION_LIMIT_REACHED",
        "message": "Live chat duration limit reached",
    }


def create_business_error_response(
    error_info: Dict[str, Any], extra_data: Optional[Dict[str, Any]] = None
) -> APIResponse[Dict[str, Any]]:
    """
    创建统一格式的业务错误响应

    Args:
        error_info: 包含code, error_code, message的错误信息字典
        extra_data: 额外数据

    Returns:
        APIResponse
    """
    # 构建错误数据
    error_data = {
        "error_code": error_info["error_code"],
        "description": error_info["message"],
    }

    # 添加额外数据
    if extra_data:
        error_data.update(extra_data)

    return APIResponse.error(
        message=error_info["message"], code=error_info["code"], data=error_data
    )
