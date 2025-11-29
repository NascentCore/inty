import enum

import sqlalchemy as sa
from sqlalchemy import ARRAY, Column, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.models import Base


class ReportStatus(str, enum.Enum):
    PENDING = "PENDING"  # 待处理
    PROCESSING = "PROCESSING"  # 处理中
    RESOLVED = "RESOLVED"  # 已处理
    REJECTED = "REJECTED"  # 已驳回


class ReportType(str, enum.Enum):
    REPORT = "REPORT"  # 举报
    FEEDBACK = "FEEDBACK"  # 反馈


class Report(Base):
    """举报记录模型"""

    __tablename__ = "report"

    id = Column(String(100), primary_key=True, comment="举报记录ID")
    target_id = Column(String(100), nullable=False, comment="被举报对象ID")
    target_type = Column(String(50), nullable=False, comment="被举报对象类型")
    reporter_id = Column(
        String(100), ForeignKey("users.id"), nullable=False, comment="举报人ID"
    )
    reason_codes = Column(
        ARRAY(String), nullable=False, comment="举报原因代码列表"
    )
    image_urls = Column(ARRAY(String), default=[], comment="举报图片URL列表")
    description = Column(Text, nullable=True, comment="举报描述")
    status = Column(
        SAEnum(ReportStatus),
        default=ReportStatus.PENDING,
        nullable=False,
        comment="举报处理状态",
    )
    report_type = Column(
        SAEnum(ReportType),
        nullable=True,
        comment="记录类型：举报或反馈，为空时默认为 REPORT",
    )
    created_at = Column(
        DateTime(timezone=True), server_default=sa.text("now()"), comment="创建时间"
    )

    # 关系
    reporter = relationship("User", back_populates="reports")
