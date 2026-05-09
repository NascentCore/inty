from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.response import PagedResponse


class NotificationItem(BaseModel):
    """通知项"""

    id: str
    type: int
    template_id: Optional[int]
    title: Optional[str]
    content: Optional[str]
    image_urls: Optional[List[str]]
    link_urls: Optional[List[str]]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationList(PagedResponse[NotificationItem]):
    """Specific model for a paginated list of notification items."""

    pass


class NotificationQuery(BaseModel):
    """通知查询参数"""

    user_id: str
    is_read: Optional[bool] = None
    skip: int = 0
    limit: int = 20


class NotificationTemplateCreate(BaseModel):
    """创建通知模板请求"""

    type: int
    title: str
    content: Optional[str] = None
    image_urls: Optional[List[str]] = None
    link_urls: Optional[List[str]] = None
    is_active: bool = True
    request_id: Optional[str] = None


class NotificationTemplateItem(BaseModel):
    """通知模板项"""

    id: int
    type: int
    title: str
    content: Optional[str]
    image_urls: Optional[List[str]]
    link_urls: Optional[List[str]]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class NotificationSendRequest(BaseModel):
    """发送通知请求"""

    template_id: int
    all_users: bool = False
    user_ids: Optional[List[str]] = None
    params: dict[str, Any] = Field(default_factory=dict)
    request_id: Optional[str] = None
