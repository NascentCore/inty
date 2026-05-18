import enum
from typing import Any, Optional

import sqlalchemy as sa
from pydantic import BaseModel
from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.utils.image import ImageSize


class ResourceType(str, enum.Enum):
    """资源类型"""

    IMAGE = "IMAGE"
    VOICE = "VOICE"
    VIDEO = "VIDEO"


class Resource(Base):
    """资源模型"""

    __tablename__ = "resources"

    url = Column(String, nullable=False, primary_key=True, index=True)
    type = Column(Enum(ResourceType))
    resource_metadata = Column(JSON)  # 存储资源的元数据，如尺寸、格式等
    created_at = Column(
        DateTime(timezone=True), server_default=sa.text("now()")
    )
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text("now()"))

    # 外键
    user_id = Column(String, ForeignKey("users.id"))
    agent_id = Column(String, ForeignKey("agents.id"))

    # 关系
    user = relationship("User", back_populates="resources")
    agent = relationship("Agent", back_populates="resources")


class ImageResourceMetadata(BaseModel):
    """
    图像资源元数据模型

    用于定义 Resource 表中 resource_metadata JSON 字段的结构，
    当 Resource.type = ResourceType.IMAGE 时使用此模型。

    对应数据库表：resources
    对应字段：resource_metadata (JSON)
    对应类型：ResourceType.IMAGE
    """

    creator: str
    size: ImageSize
    content_type: str
    byte_size: int
    compressed: bool
    uncompressed_image_url: Optional[str] = None
    cropped: bool
    uncropped_image_url: Optional[str] = None
    gcs_url: Optional[str] = None
    generation_prompt: Optional[str] = None
    generation_model: Optional[str] = None
    text_to_image_request: Optional[dict[str, Any]] = None
    reference_image_url: Optional[str] = None  # 生成图片时使用的参考图
    user_reference_image_url: Optional[str] = None  # 用户上传自拍作为额外参考图
    reference_image_urls: Optional[list[str]] = None  # 参与生图的全部参考图 URL
    only_include_ai_character: Optional[bool] = (
        None  # 无用户参考图时为 True，用于兜底候选过滤
    )
    langsmith_trace_id: Optional[str] = None
    langsmith_trace_url: Optional[str] = None

    class Config:
        from_attributes = True
