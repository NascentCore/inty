from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, field_serializer
from datetime import datetime

from app.models.agent import AgentVisibility, AgentStatus
from app.models.user import Gender
from app.schemas.user import User

class ModelConfig(BaseModel):
    """AI模型配置"""
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperature for response generation")
    max_tokens: Optional[int] = Field(None, ge=1, le=8192, description="Maximum tokens in response")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Top-p sampling parameter")
    top_k: Optional[int] = Field(None, ge=1, description="Top-k sampling parameter")
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="Presence penalty")
    
    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        if v is not None and (v < 0.0 or v > 2.0):
            raise ValueError('Temperature must be between 0.0 and 2.0')
        return v
    
    @field_validator('top_p')
    @classmethod
    def validate_top_p(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError('Top-p must be between 0.0 and 1.0')
        return v

class AgentBase(BaseModel):
    """AI角色基础模型"""
    name: str
    gender: str
    avatar: Optional[str] = None
    background: Optional[str] = None
    background_images: Optional[List[str]] = None
    voice_id: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    intro: Optional[str] = None
    opening: Optional[str] = None
    visibility: AgentVisibility = AgentVisibility.PUBLIC
    photos: Optional[List[str]] = None
    category: Optional[str] = None
    
    # Legacy字段 (已废弃)
    prompt: Optional[str] = Field(None, description="已废弃 - 请使用personality字段代替", deprecated=True)
    
    # 主提示词和模式提示词字段
    main_prompt: Optional[str] = Field(None, description="主提示词 - 作为第一个system message，覆盖全局默认主提示词")
    mode_prompt: Optional[str] = Field(None, description="模式提示词 - 放在角色卡提示词后面，覆盖全局默认模式提示词")
    
    # 角色卡相关字段 (推荐使用)
    character_card_spec: Optional[str] = None
    personality: Optional[str] = Field(None, description="角色性格特点 (推荐)")
    scenario: Optional[str] = Field(None, description="背景设定 (推荐)")
    message_example: Optional[str] = Field(None, description="对话示例")
    creator_notes: Optional[str] = Field(None, description="创作者备注")
    post_history_instructions: Optional[str] = None
    alternate_greetings: Optional[List[str]] = None
    character_book: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    character_version: Optional[str] = None
    extensions: Optional[Dict[str, Any]] = None
    
    # 模型配置
    llm_config: Optional[ModelConfig] = None

class AgentCreate(AgentBase):
    """创建AI角色
    
    推荐使用方式：
    1. 使用personality + scenario字段构建角色
    2. 添加first_message作为开场白
    3. 可选添加message_example展示对话风格
    
    兼容性说明：
    - 仍支持使用prompt字段 (legacy模式)
    - 优先级：角色卡字段 > prompt字段
    """
    pass

class AgentUpdate(AgentBase):
    """更新AI角色"""
    name: Optional[str] = None
    gender: Optional[str] = None
    visibility: Optional[AgentVisibility] = None
    prompt: Optional[str] = Field(None, description="已废弃 - 请使用personality字段代替", deprecated=True)
    
    # 主提示词和模式提示词字段
    main_prompt: Optional[str] = None
    mode_prompt: Optional[str] = None
    
    # 角色卡相关字段
    personality: Optional[str] = None
    scenario: Optional[str] = None
    message_example: Optional[str] = None
    creator_notes: Optional[str] = None
    post_history_instructions: Optional[str] = None
    alternate_greetings: Optional[List[str]] = None
    character_book: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    character_version: Optional[str] = None
    extensions: Optional[Dict[str, Any]] = None
    
    # 模型配置
    llm_config: Optional[ModelConfig] = None

class AgentInDB(AgentBase):
    """数据库中的AI角色"""
    id: str
    readable_id: str
    status: AgentStatus
    creator_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_serializer('created_at')
    def serialize_created_at(self, created_at: datetime) -> str:
        """格式化创建时间为 yy-mm-dd hh:mm"""
        return created_at.strftime('%y-%m-%d %H:%M')
    
    @field_serializer('updated_at')
    def serialize_updated_at(self, updated_at: Optional[datetime]) -> Optional[str]:
        """格式化更新时间为 yy-mm-dd hh:mm"""
        if updated_at is None:
            return None
        return updated_at.strftime('%y-%m-%d %H:%M')

    class Config:
        from_attributes = True

class Agent(AgentInDB):
    """AI角色"""
    is_followed: bool = False
    follower_count: int = 0
    creator: Optional[User] = None

class AgentList(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[Agent]

class BackgroundGenerateRequest(BaseModel):
    """背景生成请求"""
    prompt: str 
    count: int = Field(default=4, ge=1, le=4, description="Number of images to generate (1-4)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "A beautiful mountain landscape with sunset",
                "count": 6
            }
        } 

class CreatorAgentStats(BaseModel):
    """创建者的公共角色统计信息"""
    creator_id: str
    public_agents_count: int
    total_public_agents_follows: int
    
    class Config:
        from_attributes = True 