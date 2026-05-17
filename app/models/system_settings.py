import enum

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Enum, Index, String, Text

from app.models.base import Base


class SettingType(str, enum.Enum):
    """配置类型"""

    STRING = "STRING"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    JSON = "JSON"


class SettingCategory(str, enum.Enum):
    """配置分类"""

    SUBSCRIPTION_LIMITS = "SUBSCRIPTION_LIMITS"
    SYSTEM_FEATURES = "SYSTEM_FEATURES"
    SECURITY = "SECURITY"
    GENERAL = "GENERAL"


class SystemSettings(Base):
    """系统配置表"""

    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True, comment="配置键名")
    value = Column(Text, nullable=False, comment="配置值")
    value_type = Column(
        Enum(SettingType),
        nullable=False,
        default=SettingType.STRING,
        comment="值类型",
    )
    category = Column(
        Enum(SettingCategory),
        nullable=False,
        default=SettingCategory.GENERAL,
        comment="配置分类",
    )
    description = Column(Text, comment="配置描述")
    default_value = Column(Text, comment="默认值")

    # 元数据
    is_system = Column(sa.Boolean, default=False, comment="是否为系统内置配置")
    is_readonly = Column(sa.Boolean, default=False, comment="是否只读")

    # 操作记录
    updated_by = Column(String, comment="最后更新者ID")

    # 时间戳
    created_at = Column(
        DateTime(timezone=True),
        server_default=sa.text("now()"),
        comment="创建时间",
    )
    updated_at = Column(
        DateTime(timezone=True), onupdate=sa.text("now()"), comment="更新时间"
    )

    # 索引
    __table_args__ = (
        Index("ix_system_settings_category", "category"),
        Index("ix_system_settings_updated_at", "updated_at"),
    )

    def __repr__(self):
        return f"<SystemSettings(key={self.key}, value={self.value}, type={self.value_type})>"

    @property
    def parsed_value(self):
        """根据类型解析值"""
        if self.value_type == SettingType.INTEGER:
            return int(self.value)
        elif self.value_type == SettingType.FLOAT:
            return float(self.value)
        elif self.value_type == SettingType.BOOLEAN:
            return self.value.lower() in ("true", "1", "yes", "on")
        elif self.value_type == SettingType.JSON:
            import json

            return json.loads(self.value)
        else:  # STRING
            return self.value
