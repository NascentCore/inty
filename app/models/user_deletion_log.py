from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy import ARRAY, JSON, Column, DateTime, Index, String

from app.db.base_class import Base


class UserDeletionLog(Base):
    """用户删除审计日志模型"""
    __tablename__ = "user_deletion_logs"

    id = Column(String, primary_key=True, comment="删除日志ID")
    user_id = Column(String, nullable=False, comment="被删除的用户ID")
    original_user_data = Column(JSON, comment="原始用户数据快照")
    deletion_reason = Column(String(255), comment="删除原因")
    deletion_type = Column(String(50), nullable=False, default="user_requested", comment="删除类型：user_requested, admin_deletion, compliance")
    anonymized_fields = Column(ARRAY(String), comment="已匿名化的字段列表")
    subscription_status_at_deletion = Column(String(50), comment="删除时订阅状态")
    related_data_action = Column(String(100), comment="关联数据处理方式")
    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment="日志创建时间")
    processed_at = Column(DateTime(timezone=True), comment="处理完成时间")
    processor_id = Column(String, comment="处理者ID（用户本人或管理员）")

    # 索引
    __table_args__ = (
        Index('ix_user_deletion_logs_user_id', 'user_id'),
        Index('ix_user_deletion_logs_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<UserDeletionLog(id={self.id}, user_id={self.user_id}, deletion_type={self.deletion_type})>"