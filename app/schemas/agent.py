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
    background: Optional[str] = None
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
    follower_count: int = 0
    creator: Optional[User] = None
    creator_public_agents_count: Optional[int] = None
    creator_total_public_agents_follows: Optional[int] = None

class AgentList(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[Agent]

class BackgroundGenerateRequest(BaseModel):
    """背景生成请求"""
    prompt: str 

class CreatorAgentStats(BaseModel):
    """创建者的公共角色统计信息"""
    creator_id: str
    public_agents_count: int
    total_public_agents_follows: int
    
    class Config:
        from_attributes = True 