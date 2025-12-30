from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationData(BaseModel, Generic[T]):
    """分页数据结构"""

    list: List[T] = []  # 数据列表
    total: int = 0  # 总记录数
    page: int = 1  # 当前页码
    page_size: int = 10  # 每页数量
    total_pages: int = 0  # 总页数


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
class WIPBusinessErrorCodeEnum(str, Enum):
    """业务错误码枚举类型，用于返回错误信息给前端"""

    SUBSCRIPTION_REQUIRED = "SUBSCRIPTION_REQUIRED"
    IMAGE_GENERATION_LIMIT_REACHED = "IMAGE_GENERATION_LIMIT_REACHED"
    AGENT_CREATION_LIMIT_REACHED = "AGENT_CREATION_LIMIT_REACHED"
    VOICE_GENERATION_LIMIT_REACHED = "VOICE_GENERATION_LIMIT_REACHED"
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


# 业务错误消息定义
BUSINESS_ERROR_MESSAGES = {
    BusinessErrorCode.SUBSCRIPTION_REQUIRED[
        "code"
    ]: BusinessErrorCode.SUBSCRIPTION_REQUIRED["message"],
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
