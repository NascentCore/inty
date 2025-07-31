from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel

from app.models.report import ReportStatus


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
    reason_ids: List[int]
    image_urls: Optional[List[str]] = []
    description: Optional[str] = None


class ReportQuery(BaseModel):
    reason_ids: Optional[List[int]] = None
    target_id: Optional[str] = None
    target_type: Optional[TargetType] = None
    status: Optional[ReportStatus] = None
    reporter_id: Optional[str] = None
    skip: int = 0
    limit: int = 100


class ReportOut(BaseModel):
    id: str
    target_id: str
    target_type: str
    reporter_id: str
    reason_ids: List[int]
    reason_codes: List[str]
    image_urls: List[str]
    description: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
