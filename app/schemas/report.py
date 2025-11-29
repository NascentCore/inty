from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from app.models.report import ReportStatus, ReportType
from app.schemas.response import PagedResponse


class TargetType(str, Enum):
    user = "USER"
    agent = "AGENT"


class ReportCreate(BaseModel):
    target_id: str
    target_type: TargetType
    reason_codes: Optional[List[str]] = Field(
        default=None, description="举报/反馈原因的字符串 ID"
    )
    reason_ids: Optional[List[int]] = Field(
        default=None,
        description="兼容旧版 App 的整型原因 ID（已废弃）",
        deprecated=True,
    )
    image_urls: Optional[List[str]] = []
    description: Optional[str] = None
    request_id: Optional[str] = None
    report_type: Optional[ReportType] = None

    @model_validator(mode="after")
    def validate_reason_choice(self) -> "ReportCreate":
        if not self.reason_codes and not self.reason_ids:
            raise ValueError("reason_codes 或 reason_ids 至少需要提供一个")
        return self


class ReportQuery(BaseModel):
    reason_codes: Optional[List[str]] = None
    reason_ids: Optional[List[int]] = Field(
        default=None, description="兼容旧版的整型原因 ID", deprecated=True
    )
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
