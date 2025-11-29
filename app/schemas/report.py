from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel

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


class ReportCreate(BaseModel):
    target_id: str
    target_type: TargetType
    reason_ids: Optional[List[int]] = None  # DEPRECATED: 使用 reason_codes 代替
    reason_codes: Optional[List[str]] = (
        None  # 如果未提供且提供了 reason_ids，将从 reason_ids 转换
    )
    image_urls: Optional[List[str]] = []
    description: Optional[str] = None
    request_id: Optional[str] = None
    report_type: Optional[ReportType] = None


class ReportQuery(BaseModel):
    reason_ids: Optional[List[int]] = None  # DEPRECATED: 使用 reason_codes 代替
    reason_codes: Optional[List[str]] = None
    target_id: Optional[str] = None
    target_type: Optional[TargetType] = None
    status: Optional[ReportStatus] = None
    reporter_id: Optional[str] = None
    report_type: Optional[ReportType] = None
    skip: int = 0
    limit: int = 100


class ReportOut(BaseModel):
    id: str
    target_id: str
    target_type: str
    reporter_id: str
    reason_ids: List[int]  # DEPRECATED: 使用 reason_codes 代替
    reason_codes: List[str]
    image_urls: List[str]
    description: Optional[str]
    status: str
    report_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ReportsList(PagedResponse[ReportOut]):
    """Specific model for a paginated list of report items."""

    pass
