import enum
from datetime import UTC, datetime

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class NotificationTemplateType(str, enum.Enum):
    """通知模板类型"""

    TEXT_WITH_LINK = "TEXT_WITH_LINK"  # 文本+链接
    IMAGE_WITH_LINK = "IMAGE_WITH_LINK"  # 图片+链接
    TEXT_ONLY = "TEXT_ONLY"  # 文本
    IMAGE_ONLY = "IMAGE_ONLY"  # 图片
    IMAGE_TEXT_LINK = "IMAGE_TEXT_LINK"  # 图片+文本+链接


# 类型映射字典
TEMPLATE_TYPE_MAP = {
    NotificationTemplateType.TEXT_WITH_LINK: 1,
    NotificationTemplateType.IMAGE_WITH_LINK: 2,
    NotificationTemplateType.TEXT_ONLY: 3,
    NotificationTemplateType.IMAGE_ONLY: 4,
    NotificationTemplateType.IMAGE_TEXT_LINK: 5,
}

# 反向映射字典
TEMPLATE_TYPE_REVERSE_MAP = {v: k for k, v in TEMPLATE_TYPE_MAP.items()}


# DEPRECATED: 系统通知的功能并为投入使用，这个表从来没有被使用过，
# 如果做通知，在其他系统实现，不会在服务后端来实现
class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True)
    type = Column(
        Integer, nullable=False
    )  # 1: 文本+链接, 2: 图片+链接, 3: 文本, 4: 图片, 5: 图片+文本+链接
    title = Column(Text, nullable=False)
    content = Column(Text)  # 通知内容模板，支持动态参数
    image_urls = Column(ARRAY(String))  # 可为空，支持多个图片
    link_urls = Column(ARRAY(String))  # 可为空，支持多个链接
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # 索引
    __table_args__ = (
        Index("ix_notification_templates_is_active", "is_active"),
    )

    # 关联关系
    notifications = relationship("UserNotification", back_populates="template")

    def __repr__(self):
        return f"<NotificationTemplate(id={self.id}, type={self.type}, title={self.title})>"


# DEPRECATED: 系统推送设计不明，是否需要此表格不清楚，默认不应该在没有计划之前就开始做实施；计划删除
class UserNotification(Base):
    __tablename__ = "user_notifications"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    template_id = Column(
        Integer, ForeignKey("notification_templates.id", ondelete="SET NULL")
    )
    type = Column(
        Integer, nullable=False
    )  # 1: 文本+链接, 2: 图片+链接, 3: 文本, 4: 图片, 5: 图片+文本+链接
    dynamic_params = Column(JSON)  # 可选：保留原始动态参数记录
    title = Column(Text)  # 通知标题
    content = Column(Text, nullable=False)  # 通知内容
    image_urls = Column(ARRAY(String))  # 实际使用图片
    link_urls = Column(ARRAY(String))  # 实际使用链接
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    created_at = Column(
        DateTime, default=lambda: datetime.now()
    )  # 使用 naive datetime
    deleted_at = Column(DateTime)

    # 索引
    __table_args__ = (
        Index("ix_user_notifications_user_id", "user_id"),
        Index("ix_user_notifications_template_id", "template_id"),
        Index("ix_user_notifications_is_read", "is_read"),
        # 部分索引：只索引已删除的记录
        Index(
            "ix_user_notifications_deleted_at",
            "deleted_at",
            postgresql_where=text("deleted_at IS NOT NULL"),
        ),
        # 复合索引：用户未读通知查询优化
        Index("ix_user_notifications_user_read", "user_id", "is_read"),
        # 复合索引：用户通知时间排序优化
        Index("ix_user_notifications_user_created", "user_id", "created_at"),
    )

    # 关联关系
    template = relationship(
        "NotificationTemplate", back_populates="notifications"
    )
    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<UserNotification(id={self.id}, user_id={self.user_id}, template_id={self.template_id})>"
