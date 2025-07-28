import enum

import sqlalchemy as sa
from sqlalchemy import ARRAY, Boolean, Column, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class ReportReason(Base):
    """举报原因模型"""
    __tablename__ = "report_reason"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, comment="举报原因代码")
    description = Column(Text, nullable=True, comment="举报原因描述")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text('now()'), comment="更新时间")

    # 关系
    # reports = relationship("Report", back_populates="reasons")


class ReportStatus(str, enum.Enum):
    PENDING = "PENDING"      # 待处理
    PROCESSING = "PROCESSING" # 处理中
    RESOLVED = "RESOLVED"    # 已处理
    REJECTED = "REJECTED"    # 已驳回


class Report(Base):
    """举报记录模型"""
    __tablename__ = "report"

    id = Column(String(100), primary_key=True, comment="举报记录ID")
    target_id = Column(String(100), nullable=False, comment="被举报对象ID")
    target_type = Column(String(50), nullable=False, comment="被举报对象类型")
    reporter_id = Column(String(100), ForeignKey("users.id"), nullable=False, comment="举报人ID")
    reason_ids = Column(ARRAY(Integer), nullable=False, comment="举报原因ID列表")
    image_urls = Column(ARRAY(String), default=[], comment="举报图片URL列表")
    description = Column(Text, nullable=True, comment="举报描述")
    status = Column(SAEnum(ReportStatus), default=ReportStatus.PENDING, nullable=False, comment="举报处理状态")
    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'), comment="创建时间")

    # 关系
    reporter = relationship("User", back_populates="reports")
    # reasons = relationship("ReportReason", secondary="report_reason_association", back_populates="reports") 