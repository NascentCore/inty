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
    code: int
    error_code: str
    message: str

    class Config:
        allow_mutation = False

    def build_error_data(
        self, extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        error_data: Dict[str, Any] = {
            "error_code": self.error_code,
            "description": self.message,
        }
        if extra_data:
            error_data.update(extra_data)
        return error_data

    def to_api_response(
        self, extra_data: Optional[Dict[str, Any]] = None
    ) -> "APIResponse[Dict[str, Any]]":
        return APIResponse.error(
            message=self.message,
            code=self.code,
            data=self.build_error_data(extra_data),
        )


# 业务错误码定义
class BusinessErrorCode:
    SUBSCRIPTION_REQUIRED = BizError(
        code=10001001,
        error_code="SUBSCRIPTION_REQUIRED",
        message="Subscription required",
    )
    IMAGE_GENERATION_LIMIT_REACHED = BizError(
        code=10001002,
        error_code="IMAGE_GENERATION_LIMIT_REACHED",
        message="Image generation limit reached",
    )
    AGENT_CREATION_LIMIT_REACHED = BizError(
        code=10001003,
        error_code="AGENT_CREATION_LIMIT_REACHED",
        message="Character creation limit reached",
    )
    VOICE_GENERATION_LIMIT_REACHED = BizError(
        code=10001004,
        error_code="VOICE_GENERATION_LIMIT_REACHED",
        message="Voice generation limit reached",
    )
    GUEST_LOGIN_REQUIRED = BizError(
        code=10001005,
        error_code="GUEST_LOGIN_REQUIRED",
        message="Guest login required - Please sign in with Google",
    )


# 业务错误消息定义
BUSINESS_ERROR_MESSAGES = {
    BusinessErrorCode.SUBSCRIPTION_REQUIRED.code:
        BusinessErrorCode.SUBSCRIPTION_REQUIRED.message,
}


def create_business_error_response(
    error_info: BizError, extra_data: Optional[Dict[str, Any]] = None
) -> APIResponse[Dict[str, Any]]:
    """
    创建统一格式的业务错误响应

    Args:
        error_info: BizError 实例
        extra_data: 额外数据

    Returns:
        APIResponse
    """
    return error_info.to_api_response(extra_data)
