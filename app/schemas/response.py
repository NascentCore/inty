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


# 业务错误码定义
class BusinessErrorCode:
    SUBSCRIPTION_REQUIRED = {
        "code": 10001001,
        "error_code": "SUBSCRIPTION_REQUIRED",
        "message": "Subscription required"
    }


# 业务错误消息定义
BUSINESS_ERROR_MESSAGES = {
    BusinessErrorCode.SUBSCRIPTION_REQUIRED["code"]: BusinessErrorCode.SUBSCRIPTION_REQUIRED["message"],
}


def create_business_error_response(
    error_info: Dict[str, Any],
    extra_data: Optional[Dict[str, Any]] = None
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
        message=error_info["message"], 
        code=error_info["code"], 
        data=error_data
    )
