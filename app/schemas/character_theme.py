"""角色主题专区 Schema 定义"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.character_theme import CharacterThemeVisibility
from app.schemas.agent import Agent


class CharacterThemeBase(BaseModel):
    """角色主题专区基础模型"""

    name: str = Field(..., max_length=255, description="专区名称")
    description: Optional[str] = Field(None, description="专区描述")
    background_image_url: Optional[str] = Field(
        None, description="背景图URL地址"
    )
    visibility: Optional[CharacterThemeVisibility] = Field(
        None, description="可见性：第一展示、第二展示、不可见"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Theme section name cannot be empty")
        if len(v) > 255:
            raise ValueError(
                "Theme section name must not exceed 255 characters"
            )
        return v.strip()


class CharacterThemeCreate(CharacterThemeBase):
    """创建角色主题专区请求模型"""

    visibility: Optional[CharacterThemeVisibility] = Field(
        default=CharacterThemeVisibility.HIDDEN,
        description="可见性：第一展示、第二展示、不可见（默认：不可见）",
    )


class CharacterThemeUpdate(BaseModel):
    """更新角色主题专区请求模型"""

    name: Optional[str] = Field(None, max_length=255, description="专区名称")
    description: Optional[str] = Field(None, description="专区描述")
    background_image_url: Optional[str] = Field(
        None, description="背景图URL地址"
    )
    visibility: Optional[CharacterThemeVisibility] = Field(
        None, description="可见性：第一展示、第二展示、不可见"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Theme section name cannot be empty")
            if len(v) > 255:
                raise ValueError(
                    "Theme section name must not exceed 255 characters"
                )
            return v.strip()
        return v


class CharacterThemeAgent(BaseModel):
    """专区中的角色信息"""

    agent_id: str = Field(..., description="角色ID")
    order_index: int = Field(..., description="角色在专区中的顺序（从0开始）")
    agent: Optional[Agent] = Field(None, description="角色详细信息")

    class Config:
        from_attributes = True


class CharacterTheme(CharacterThemeBase):
    """角色主题专区完整响应模型"""

    id: str = Field(..., description="专区ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    visibility: CharacterThemeVisibility = Field(
        ..., description="可见性：第一展示、第二展示、不可见"
    )
    agents: List[CharacterThemeAgent] = Field(
        default_factory=list, description="专区中的角色列表（按顺序）"
    )

    class Config:
        from_attributes = True


class AddAgentToThemeRequest(BaseModel):
    """添加角色到专区请求"""

    agent_id: str = Field(..., description="要添加的角色ID")


class ReorderAgentsRequest(BaseModel):
    """调整角色顺序请求"""

    agent_ids: List[str] = Field(..., description="角色ID列表，按新顺序排列")

    @field_validator("agent_ids")
    @classmethod
    def validate_agent_ids(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("Agent ID list cannot be empty")
        if len(v) != len(set(v)):
            raise ValueError("Agent ID list must not contain duplicates")
        return v
