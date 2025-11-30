import enum

import sqlalchemy as sa
from sqlalchemy import ARRAY, Boolean, Column, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models import Base

# 举报原因 ID 到代码的映射（硬编码，不再使用数据库表）
# 对应关系与 Android 端保持一致（参考 ReportViewModel.kt）：
#   1 -> SENSITIVE_CONTENT (Sensitive or sexual content)
#   2 -> MISINFORMATION (Misinformation)
#   3 -> FRAUD_SCAMS (Fraud or scams)
#   4 -> PRIVACY_VIOLATION (Violation of privacy)
#   5 -> HARMFUL_MINORS (Harmful to minors)
#   6 -> IP_VIOLATION (Violations of my intellectual property)
REASON_ID_TO_CODE = {
    1: "SENSITIVE_CONTENT",
    2: "MISINFORMATION",
    3: "FRAUD_SCAMS",
    4: "PRIVACY_VIOLATION",
    5: "HARMFUL_MINORS",
    6: "IP_VIOLATION",
}

# 反馈原因 ID 到代码的映射（硬编码，不再使用数据库表）
# 对应关系与 Android 端保持一致（参考 ReportViewModel.kt）：
#   0 -> OTHER (Other, please describe below)
#   1 -> CHAT_NOT_NATURAL (Chat replies don't feel natural / off-topic)
#   2 -> CHARACTER_MISMATCH (The character doesn't match its persona)
#   3 -> APP_SLOW (The app is slow or gets stuck)
#   4 -> FEATURE_HARD_TO_FIND (I couldn't find / how to use this feature)
#   5 -> UI_INCONVENIENT (UI or interaction feels inconvenient)
#   6 -> NEW_FEATURE (I'd like to see a new feature or improvement)
FEEDBACK_REASON_ID_TO_CODE = {
    0: "OTHER",
    1: "CHAT_NOT_NATURAL",
    2: "CHARACTER_MISMATCH",
    3: "APP_SLOW",
    4: "FEATURE_HARD_TO_FIND",
    5: "UI_INCONVENIENT",
    6: "NEW_FEATURE",
}


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
    reason_ids = Column(
        ARRAY(Integer),
        nullable=True,
        comment="[DEPRECATED] 举报原因ID列表，使用 reason_codes 代替",
    )
    reason_codes = Column(ARRAY(String), nullable=True, comment="举报原因代码列表，用来替代 reason_ids，因为 id 很难维护")
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
    # reasons = relationship("ReportReason", secondary="report_reason_association", back_populates="reports")
