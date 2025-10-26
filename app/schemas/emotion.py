from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class EmotionListItem(BaseModel):
    name: str = Field(description="情绪名称，大小写固定")
    description: str = Field(description="简短中文描述")


class EmotionListResponse(BaseModel):
    emotions: List[EmotionListItem]


class EmotionMappingSetRequest(BaseModel):
    mapping: Dict[str, str] = Field(
        description="情绪到图片URL的映射，key需来自 /list 返回的 name"
    )
    replace: bool = Field(default=True, description="True整体替换；False合并覆盖")


class EmotionMappingResponse(BaseModel):
    mapping: Dict[str, str]


class EmotionSelectRequest(BaseModel):
    utterance: str = Field(description="角色台词")
    context: Optional[str] = Field(default=None, description="上下文/场景")
    character_state: Optional[str] = Field(default=None, description="当前角色状态")


class EmotionSelectResult(BaseModel):
    emotion: str = Field(description="选中的情绪名称")
    image_url: Optional[str] = Field(default=None, description="匹配到的图片URL")
