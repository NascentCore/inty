from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.models.resource import ResourceType


class ResourceBase(BaseModel):
    """资源基础模型"""
    type: ResourceType
    url: str
    resource_metadata: Optional[Dict[str, Any]] = None


class ResourceCreate(ResourceBase):
    """创建资源"""
    pass


class ResourceUpdate(BaseModel):
    """更新资源"""
    type: Optional[ResourceType] = None
    url: Optional[str] = None
    resource_metadata: Optional[Dict[str, Any]] = None


class ResourceInDB(ResourceBase):
    """数据库中的资源"""
    id: str
    user_id: str
    agent_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Resource(ResourceInDB):
    """资源"""
    pass 