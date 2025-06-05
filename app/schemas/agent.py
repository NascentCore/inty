from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.models.agent import AgentVisibility, AgentStatus
from app.models.user import Gender
from app.schemas.user import User

class AgentBase(BaseModel):
    """AI角色基础模型"""
    name: str
    gender: str
    avatar: Optional[str] = None
    voice_id: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    intro: Optional[str] = None
    opening: Optional[str] = None
    visibility: AgentVisibility = AgentVisibility.PUBLIC
    photos: Optional[List[str]] = None
    category: Optional[str] = None
    prompt: Optional[str] = None

class AgentCreate(AgentBase):
    """创建AI角色"""
    pass

class AgentUpdate(AgentBase):
    """更新AI角色"""
    name: Optional[str] = None
    gender: Optional[str] = None
    visibility: Optional[AgentVisibility] = None
    prompt: Optional[str] = None

class AgentInDB(AgentBase):
    """数据库中的AI角色"""
    id: str
    status: AgentStatus
    creator_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Agent(AgentInDB):
    """AI角色"""
    is_followed: bool = False
    creator: Optional[User] = None

class AgentList(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[Agent] 