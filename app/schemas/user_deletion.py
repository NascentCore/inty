from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AccountDeletionRequest(BaseModel):
    """账户删除请求"""

    reason: Optional[str] = Field(None, max_length=255, description="删除原因")
    request_id: Optional[str] = None

    class Config:
        json_schema_extra = {"example": {"reason": "隐私关注"}}


class AccountDeletionResponse(BaseModel):
    """账户删除响应"""

    success: bool = Field(..., description="是否删除成功")
    message: str = Field(..., description="删除结果消息")
    user_id: str = Field(..., description="用户ID")
    deletion_log_id: Optional[str] = Field(None, description="删除日志ID")
    anonymized_fields: Optional[List[str]] = Field(
        None, description="已匿名化的字段列表"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "账户删除成功",
                "user_id": "user_123",
                "deletion_log_id": "del_log_456",
                "anonymized_fields": ["email", "phone", "nickname"],
            }
        }


class DeletionCheckResponse(BaseModel):
    """删除检查响应"""

    can_delete: bool = Field(..., description="是否可以删除")
    error_message: Optional[str] = Field(None, description="错误信息")
    active_subscription: Optional[bool] = Field(
        None, description="是否有活跃订阅"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "can_delete": False,
                "error_message": "存在活跃订阅，请先取消订阅后再删除账户",
                "active_subscription": True,
            }
        }


class UserDeletionLogSchema(BaseModel):
    """用户删除日志Schema"""

    id: str = Field(..., description="删除日志ID")
    user_id: str = Field(..., description="被删除的用户ID")
    original_user_data: Optional[Dict[str, Any]] = Field(
        None, description="原始用户数据快照"
    )
    deletion_reason: Optional[str] = Field(None, description="删除原因")
    deletion_type: str = Field(..., description="删除类型")
    anonymized_fields: Optional[List[str]] = Field(
        None, description="已匿名化的字段列表"
    )
    subscription_status_at_deletion: Optional[str] = Field(
        None, description="删除时订阅状态"
    )
    related_data_action: Optional[str] = Field(
        None, description="关联数据处理方式"
    )
    created_at: datetime = Field(..., description="日志创建时间")
    processed_at: Optional[datetime] = Field(None, description="处理完成时间")
    processor_id: Optional[str] = Field(None, description="处理者ID")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "del_log_123",
                "user_id": "user_456",
                "deletion_reason": "用户主动删除",
                "deletion_type": "user_requested",
                "anonymized_fields": ["email", "phone", "nickname"],
                "subscription_status_at_deletion": "inactive",
                "related_data_action": "anonymized",
                "created_at": "2025-07-18T12:00:00Z",
                "processed_at": "2025-07-18T12:01:00Z",
                "processor_id": "user_456",
            }
        }


class AnonymizationStatsResponse(BaseModel):
    """匿名化统计响应"""

    agents_anonymized: int = Field(..., description="匿名化的Agent数量")
    messages_anonymized: int = Field(..., description="匿名化的消息数量")
    chats_updated: int = Field(..., description="更新的聊天数量")

    class Config:
        json_schema_extra = {
            "example": {
                "agents_anonymized": 5,
                "messages_anonymized": 127,
                "chats_updated": 8,
            }
        }
