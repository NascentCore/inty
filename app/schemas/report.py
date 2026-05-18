"""Defines request and response schemas for report and feedback APIs."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.report import ReportStatus, ReportType
from app.schemas.response import PagedResponse


class ReportReason(BaseModel):
    id: int
    code: str
    description: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class TargetType(str, Enum):
    user = "USER"
    agent = "AGENT"


class ReasonCode(str, Enum):
    """
    原因代码枚举，包含 Report 和 Feedback 的所有可能值
    这些枚举值经过 stainless 转换进入到 android_app 内的表单展示页面
    """

    # Report 原因代码
    SENSITIVE_CONTENT = "SENSITIVE_CONTENT"
    MISINFORMATION = "MISINFORMATION"
    FRAUD_SCAMS = "FRAUD_SCAMS"
    PRIVACY_VIOLATION = "PRIVACY_VIOLATION"
    HARMFUL_MINORS = "HARMFUL_MINORS"
    IP_VIOLATION = "IP_VIOLATION"

    # Feedback 原因代码
    OTHER = "OTHER"
    CHAT_NOT_NATURAL = "CHAT_NOT_NATURAL"
    CHARACTER_MISMATCH = "CHARACTER_MISMATCH"
    APP_SLOW = "APP_SLOW"
    FEATURE_HARD_TO_FIND = "FEATURE_HARD_TO_FIND"
    UI_INCONVENIENT = "UI_INCONVENIENT"
    NEW_FEATURE = "NEW_FEATURE"
    IMAGE_LOW_QUALITY = "IMAGE_LOW_QUALITY"
    IMAGE_STYLE_MISMATCH = "IMAGE_STYLE_MISMATCH"
    IMAGE_CONTENT_MISMATCH = "IMAGE_CONTENT_MISMATCH"
    IMAGE_ANATOMY_OR_STRUCTURE_ERROR = "IMAGE_ANATOMY_OR_STRUCTURE_ERROR"
    IMAGE_OTHER = "IMAGE_OTHER"


class ReportCreate(BaseModel):
    """
    Report API 端点的请求数据结构。
    """

    target_id: str = Field(
        ..., description="举报或者反馈的目标对象的 ID，角色或者用户的 ID。"
    )
    target_type: TargetType = Field(
        ..., description="举报或者反馈的目标对象的类型，角色或者用户。"
    )
    reason_ids: Optional[List[int]] = None  # DEPRECATED: 使用 reason_codes 代替
    reason_codes: Optional[List[ReasonCode]] = Field(
        None,
        description="举报或者反馈的原因代码列表。如果未提供且提供了 reason_ids，将从 reason_ids 自动转换",
    )
    image_urls: Optional[List[str]] = Field(
        default_factory=list,
        description="举报或者反馈附图的链接，该链接来自 /api/v1/images 端点上传图片返回的 gcs URL（可能是 cdn 链接）",
    )
    description: Optional[str] = Field(
        None, description="The description of the report."
    )
    request_id: Optional[str] = Field(
        None, description="The ID of the request."
    )
    report_type: Optional[ReportType] = Field(
        None, description="举报或者反馈的类型，为空时默认为 REPORT"
    )


class ReportQuery(BaseModel):
    reason_ids: Optional[List[int]] = None  # DEPRECATED: 使用 reason_codes 代替
    reason_codes: Optional[List[ReasonCode]] = None
    target_id: Optional[str] = None
    target_type: Optional[TargetType] = None
    status: Optional[ReportStatus] = None
    reporter_id: Optional[str] = None
    report_type: Optional[ReportType] = None
    order_by: Optional[str] = (
        "created_at_desc"  # created_at_desc 或 created_at_asc
    )
    skip: int = 0
    limit: int = 100


class ReportGithubIssueUpdate(BaseModel):
    github_issue: Optional[str] = Field(
        None, description="GitHub issue URL associated with this report"
    )


class ReporterUserInfo(BaseModel):
    id: str
    readable_id: Optional[str]
    nickname: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class ReportOut(BaseModel):
    id: str
    target_id: str
    target_type: str
    reporter_id: str
    reporter_user_info: Optional[ReporterUserInfo] = None
    reason_ids: List[int]  # DEPRECATED: 使用 reason_codes 代替
    reason_codes: List[str]
    image_urls: List[str]
    description: Optional[str]
    github_issue: Optional[str]
    status: str
    report_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ReportsList(PagedResponse[ReportOut]):
    """Specific model for a paginated list of report items."""

    pass


class ReportConversationGroup(BaseModel):
    """按 user_id + agent_id 分组的聊天概览。"""

    user_id: str
    agent_id: str
    agent_name: Optional[str]
    chat_count: int
    total_rounds: int
    latest_message_at: Optional[datetime]


class ReportConversationGroups(BaseModel):
    """举报关联用户的聊天分组列表。"""

    items: List[ReportConversationGroup]
    total: int


class ReportConversationMessage(BaseModel):
    """举报聊天分组内的单条消息。"""

    id: int
    chat_id: str
    message_type: str
    content: Optional[str]
    image_url: Optional[str]
    created_at: Optional[datetime]
    audio_url: Optional[str]
    meta_data: Optional[Dict[str, Any]]


class ReportConversationMessages(BaseModel):
    """举报聊天分组内按轮次分页的消息列表。"""

    user_id: str
    agent_id: str
    page: int
    size: int
    total_rounds: int
    has_more: bool
    messages: List[ReportConversationMessage]
