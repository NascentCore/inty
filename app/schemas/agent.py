from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_serializer, field_validator

from app.models.agent import AgentStatus, AgentVisibility
from app.models.user import Gender
from app.schemas.user import User


class AgentSortOption(str, Enum):
    """Agent sorting options"""
    # Ascending order of the creation time, oldest to the newest
    CREATED_ASC = "created_asc"
    # Descending order of the creation time, newest to the oldest
    CREATED_DESC = "created_desc"
    # Random order, use sort_seed to ensure consistent order
    RANDOM = "random"


class AgentSortConfig(BaseModel):
    """Agent sorting config"""

    sort: AgentSortOption = Field(default=AgentSortOption.RANDOM, description="sort option")
    sort_seed: str = Field(default="", description="Sort seed, used to ensure consistent order for the random sort option")

class ModelConfig(BaseModel):
    """AI模型配置"""

    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = Field(
        None, ge=0.0, le=2.0, description="Temperature for response generation"
    )
    max_tokens: Optional[int] = Field(
        None, ge=1, le=8192, description="Maximum tokens in response"
    )
    top_p: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Top-p sampling parameter"
    )
    top_k: Optional[int] = Field(None, ge=1, description="Top-k sampling parameter")
    frequency_penalty: Optional[float] = Field(
        None, ge=-2.0, le=2.0, description="Frequency penalty"
    )
    presence_penalty: Optional[float] = Field(
        None, ge=-2.0, le=2.0, description="Presence penalty"
    )

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v):
        if v is not None and (v < 0.0 or v > 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v

    @field_validator("top_p")
    @classmethod
    def validate_top_p(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Top-p must be between 0.0 and 1.0")
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
    opening_audio_url: Optional[str] = None
    visibility: AgentVisibility = AgentVisibility.PUBLIC
    photos: Optional[List[str]] = None
    category: Optional[str] = None

    # Legacy字段 (已废弃)
    prompt: Optional[str] = Field(
        None, description="已废弃 - 请使用personality字段代替", deprecated=True
    )

    # 主提示词和模式提示词字段
    main_prompt: Optional[str] = Field(
        None, description="主提示词 - 作为第一个system message，覆盖全局默认主提示词"
    )
    mode_prompt: Optional[str] = Field(
        None, description="模式提示词 - 放在角色卡提示词后面，覆盖全局默认模式提示词"
    )

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
    prompt: Optional[str] = Field(
        None, description="已废弃 - 请使用personality字段代替", deprecated=True
    )

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
    deleted_at: Optional[datetime] = None

    @field_serializer("created_at")
    def serialize_created_at(self, created_at: datetime) -> int:
        """序列化创建时间为时间戳"""
        return int(created_at.timestamp())

    @field_serializer("updated_at")
    def serialize_updated_at(self, updated_at: Optional[datetime]) -> Optional[int]:
        """序列化更新时间为时间戳"""
        if updated_at is None:
            return None
        return int(updated_at.timestamp())

    @field_serializer("deleted_at")
    def serialize_deleted_at(self, deleted_at: Optional[datetime]) -> Optional[int]:
        """序列化删除时间为时间戳"""
        if deleted_at is None:
            return None
        return int(deleted_at.timestamp())

    class Config:
        from_attributes = True


class Agent(AgentInDB):
    """AI角色"""

    is_followed: bool = False
    follower_count: int = 0
    connector_count: int = 0
    creator: Optional[User] = None

    @field_serializer("llm_config")
    def serialize_llm_config(
        self, llm_config: Optional[ModelConfig]
    ) -> Optional[ModelConfig]:
        """
        从settings字段中提取llm_config，数据库将 llm_config 及其他潜在
        未来添加字段放到了 settings 字段中
        """
        if llm_config is not None:
            return llm_config

        # 如果llm_config为空，尝试从settings中获取
        if self.settings and isinstance(self.settings, dict):
            settings_llm_config = self.settings.get("llm_config")
            if settings_llm_config:
                # 将settings中的llm_config转换为ModelConfig对象
                try:
                    return ModelConfig(**settings_llm_config)
                except Exception:
                    # 如果转换失败，返回None
                    return None

        return None


class AgentList(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[Agent]


class TextToImageRequest(BaseModel):
    """
    Text to image request
    """

    prompt: str = Field(
        ...,
        description=(
            "Text description of the image, typically a list of comma "
            "separated keywords/tags/properties"
        ),
    )
    negative_prompt: Optional[str] = Field(
        None,
        description=(
            "Negative prompt to avoid generating images with certain features, "
            "e.g. 'blurry, low quality, explicit, NSFW'"
        ),
    )
    enhance_prompt: Optional[bool] = Field(
        # 默认打开提示词增强，以兼容旧版本。
        # 此为方便用户生成角色形象时针对角色性别和人物进行增强，让文生图模型能生成更合规和符合 app 设定的异性恋对象角色。
        True,
        description=(
            "Whether to enhance the prompt to improve the quality of the image. "
            "The default is True for backward comaptibility. "
            "This enhancement is different than the underlying imagen API's own enhancement. "
            "This parameter is also required to allow this api to be used as a text-to-image wrapper. "
            "As a wrapper, we'll not want to apply enhancement to the prompt. "
        ),
    )
    count: int = Field(
        default=4,
        ge=1,
        le=4,
        description="Number of images to generate",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "A beautiful mountain landscape with sunset",
                "negative_prompt": "blurry, low quality, explicit, NSFW",
                "enhance_prompt": True,
                "count": 2,
            }
        }


class CreatorAgentStats(BaseModel):
    """创建者的公共角色统计信息"""

    creator_id: str
    public_agents_count: int
    total_public_agents_follows: int

    class Config:
        from_attributes = True
