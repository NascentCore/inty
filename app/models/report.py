import enum

import sqlalchemy as sa
from sqlalchemy import ARRAY, Boolean, Column, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models import Base
# DEPRECATED：表格内的数据会转为代码中的静态数据，不会在数据库中存储
class ReportReason(Base):
    """
    目前举报原因如下，会转为代码中的静态数据，不会在数据库中存储
    devdb=# select * from report_reason;
     id |                code                |              description               | is_active |          created_at           | updated_at
    ----+------------------------------------+----------------------------------------+-----------+-------------------------------+------------
      1 | SENSITIVE_OR_SEXUAL_CONTENT        | Sensitive or sexual content            | t         | 2025-06-05 11:47:00.713535+00 |
      2 | MISINFORMATION                     | Misinformation                         | t         | 2025-06-05 11:47:00.713535+00 |
      3 | FRAUD_OR_SCAMS                     | Fraud or scams                         | t         | 2025-06-05 11:47:00.713535+00 |
      4 | VIOLATION_OF_PRIVACY               | Violation of privacy                   | t         | 2025-06-05 11:47:00.713535+00 |
      5 | HARMFUL_TO_MINORS                  | Harmful to minors                      | t         | 2025-06-05 11:47:00.713535+00 |
      6 | VIOLATION_OF_INTELLECTUAL_PROPERTY | Violations of my intellectual property | t         | 2025-06-05 11:47:00.713535+00 |
    """
# TODO：删除该表。
# 原因被硬编码在应用程序中。
# 报告时，使用实际原因代码而不是原因ID。
# 应用程序目前使用原因ID来报告问题，我们需要将其更改为原因代码。
# 只有在此之后，才能删除该表。
    __tablename__ = "report_reason"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, comment="举报原因代码")
    description = Column(Text, nullable=True, comment="举报原因描述")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(
        DateTime(timezone=True), server_default=sa.text("now()"), comment="创建时间"
    )
    updated_at = Column(
        DateTime(timezone=True), onupdate=sa.text("now()"), comment="更新时间"
    )
# 关系
# 报告 = 关系("报告", back_populates="原因")


class ReportStatus(str, enum.Enum):
    PENDING = "PENDING"  # 待处理
    PROCESSING = "PROCESSING"  # 处理中
    RESOLVED = "RESOLVED"  # 已处理
    REJECTED = "REJECTED"  # 已驳回


class Report(Base):
    """举报记录模型"""

    __tablename__ = "report"

    id = Column(String(100), primary_key=True, comment="举报记录ID")
    target_id = Column(String(100), nullable=False, comment="被举报对象ID")
    target_type = Column(String(50), nullable=False, comment="被举报对象类型")
    reporter_id = Column(
        String(100), ForeignKey("users.id"), nullable=False, comment="举报人ID"
    )
    reason_ids = Column(ARRAY(Integer), nullable=False, comment="举报原因ID列表")
    image_urls = Column(ARRAY(String), default=[], comment="举报图片URL列表")
    description = Column(Text, nullable=True, comment="举报描述")
    status = Column(
        SAEnum(ReportStatus),
        default=ReportStatus.PENDING,
        nullable=False,
        comment="举报处理状态",
    )
    created_at = Column(
        DateTime(timezone=True), server_default=sa.text("now()"), comment="创建时间"
    )
# 关系
    reporter = relationship("User", back_populates="reports")
# 原因 = 关系("ReportReason", secondary="report_reason_association", back_populates="reports")
