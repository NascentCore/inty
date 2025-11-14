from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_serializer, field_validator

from app.core.agent.prompt_template import (
    has_template_variable,
    render_prompt_jinja2_template,
)
from app.models.agent import AgentStatus, AgentVisibility
from app.schemas.user import User
from app.utils.image import ImageSize


class AgentMetaData(BaseModel):
    """Agent 元数据模型"""

    score: Optional[int] = Field(None, description="Agent 评分")

    comment: Optional[str] = Field(None, max_length=1000, description="Agent 备注信息")

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v):
        if v is not None and len(v) > 1000:
            raise ValueError("Comment must not exceed 1000 characters")
        return v


class AgentSortOption(str, Enum):
    """Agent sorting options"""

    # Ascending order of the creation time, oldest to the newest
    CREATED_ASC = "created_asc"
    # Descending order of the creation time, newest to the oldest
    CREATED_DESC = "created_desc"
    # Random order, use sort_seed to ensure consistent order
    RANDOM = "random"
    # Score-based random recommendation: 6 high-score agents + 4 random agents
    SCORE_BASED_RANDOM = "score_based_random"


class AgentSortConfig(BaseModel):
    """Agent sorting config"""

    sort: AgentSortOption = Field(
        default=AgentSortOption.RANDOM, description="sort option"
    )
    sort_seed: str = Field(
        default="",
        description="Sort seed, used to ensure consistent order for the random sort option",
    )


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
    background_animated: Optional[str] = None  # 视频URL
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

    # 元数据
    meta_data: Optional[AgentMetaData] = Field(
        None, description="Agent 元数据，包含评分等信息"
    )

    @field_validator(
        "background_images", "photos", "alternate_greetings", "tags", mode="before"
    )
    @classmethod
    def convert_empty_string_to_none(cls, v):
        """将空字符串转换为 None，兼容 Dify 模板变量替换将 null 序列化为空字符串的行为"""
        if v == "":
            return None
        return v


class GenerateBackgroundAnimatedRequest(BaseModel):
    """生成背景视频请求"""

    prompt: Optional[str] = Field(
        default=None, description="视频生成提示词（可选，如果为空则从背景图自动生成）"
    )


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

    request_id: Optional[str] = None


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
    voice_id: Optional[str] = None

    # 模型配置
    llm_config: Optional[ModelConfig] = None

    # 元数据
    meta_data: Optional[AgentMetaData] = None

    request_id: Optional[str] = None


class AgentInDB(AgentBase):
    """数据库中的AI角色，与 sqlalchemy 模型一一对应"""

    id: str
    # DEPRECATED: app 显示 ID 而非 readable_id
    readable_id: str
    status: AgentStatus
    creator_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    version: int

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
    """AI角色，在 sqlalchemy 模型基础上添加额外多表查询来的数据"""

    is_followed: bool = False
    follower_count: int = 0
    connector_count: int = 0
    creator: Optional[User] = None
    # 从 resources 表中读取对应的图片尺寸；注意区分图片的字节大小，指的是文件本身的大小。
    avatar_size: Optional[ImageSize] = None
    # 从 resources 表中读取对应的图片尺寸；注意区分图片的字节大小，指的是文件本身的大小。
    background_size: Optional[ImageSize] = None
    # 当前与该 agent 对话的用户名字，用于替换 opening 和 intro 中的 {{ user }} 变量。
    # 如未制定，则使用默认的代词 "you"。
    user: Optional[str] = "you"

    # TODO: 考虑如何使用 intro 从而避免重复使用手动变量替换
    @field_serializer("intro")
    def serialize_intro(self, intro: Optional[str]) -> Optional[str]:
        """
        对intro字段进行变量替换，将 {{ char }} 替换为 agent.name
        """
        if intro and has_template_variable(intro):
            return render_prompt_jinja2_template(intro, char=self.name, user=self.user)
        return intro

    @field_serializer("opening")
    def serialize_opening(self, opening: Optional[str]) -> Optional[str]:
        """
        对opening字段进行变量替换，将 {{ char }} 替换为 agent.name，{{ user }} 替换为 "you"
        """
        if opening and has_template_variable(opening):
            return render_prompt_jinja2_template(
                opening, char=self.name, user=self.user
            )
        return opening

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

    @field_serializer("avatar")
    def serialize_avatar(self, avatar: Optional[str]) -> Optional[str]:
        """转换avatar URL为CDN URL，支持基于extension裁切数据的avatar生成"""
        try:
            from app.services.image_transform_service import image_transform_service

            # 优先检查是否存在裁切数据，如果存在则使用裁切数据而不是独立的avatar
            if (
                self.background
                and self.extensions
                and isinstance(self.extensions, dict)
                and "avatar_crop" in self.extensions
            ):

                avatar_crop_data = self.extensions["avatar_crop"]

                # 验证裁切数据的完整性
                if (
                    isinstance(avatar_crop_data, dict)
                    and all(
                        key in avatar_crop_data
                        for key in [
                            "x",
                            "y",
                            "width",
                            "height",
                            "imageWidth",
                            "imageHeight",
                        ]
                    )
                    and all(
                        isinstance(avatar_crop_data[key], (int, float))
                        for key in [
                            "x",
                            "y",
                            "width",
                            "height",
                            "imageWidth",
                            "imageHeight",
                        ]
                    )
                    and avatar_crop_data["width"] > 0
                    and avatar_crop_data["height"] > 0
                ):

                    # 创建 CroppedArea 对象
                    from app.services.image_transform_service import (
                        ImageTransformService,
                    )

                    cropped_area = ImageTransformService.CroppedArea(
                        x=int(avatar_crop_data["x"]),
                        y=int(avatar_crop_data["y"]),
                        width=int(avatar_crop_data["width"]),
                        height=int(avatar_crop_data["height"]),
                        image_width=int(avatar_crop_data["imageWidth"]),
                        image_height=int(avatar_crop_data["imageHeight"]),
                    )

                    # 使用裁切功能生成avatar URL
                    return image_transform_service.transform_cropped_avatar_url(
                        self.background, cropped_area
                    )

            # 如果没有裁切数据但有独立的avatar，使用常规转换
            if avatar:
                return image_transform_service.transform_mobile(avatar)

            return avatar

        except Exception as e:
            # 记录错误但不抛出异常，返回原始avatar
            from loguru import logger

            logger.warning(
                f"Failed to serialize avatar for agent {getattr(self, 'id', 'unknown')}: {str(e)}"
            )
            return avatar

    @field_serializer("background")
    def serialize_background(self, background: Optional[str]) -> Optional[str]:
        """转换background URL为CDN URL"""
        if not background:
            return background
        try:
            from app.services.image_transform_service import image_transform_service

            return image_transform_service.transform_desktop(background)
        except Exception:
            return background

    @field_serializer("background_images")
    def serialize_background_images(
        self, background_images: Optional[List[str]]
    ) -> Optional[List[str]]:
        """转换background_images URL列表为CDN URL"""
        if not background_images:
            return background_images
        try:
            from app.services.image_transform_service import image_transform_service

            return image_transform_service.transform_url_list(
                background_images, "desktop"
            )
        except Exception:
            return background_images

    @field_serializer("background_animated")
    def serialize_background_animated(
        self, background_animated: Optional[str]
    ) -> Optional[str]:
        """转换background_animated URL为CDN URL"""
        if not background_animated:
            return background_animated
        try:
            from app.services.image_transform_service import image_transform_service

            return image_transform_service.transform_desktop(background_animated)
        except Exception:
            return background_animated

    @field_serializer("photos")
    def serialize_photos(self, photos: Optional[List[str]]) -> Optional[List[str]]:
        """转换photos URL列表为CDN URL"""
        if not photos:
            return photos
        try:
            from app.services.image_transform_service import image_transform_service

            return image_transform_service.transform_url_list(photos, "mobile")
        except Exception:
            return photos

    @field_serializer("meta_data")
    def serialize_meta_data(
        self, meta_data: Optional[AgentMetaData]
    ) -> Optional[AgentMetaData]:
        """
        从数据库的meta_data字段中提取并转换为AgentMetaData对象
        """
        if meta_data is not None:
            return meta_data

        # 如果meta_data为空，尝试从数据库的meta_data字段获取
        if (
            hasattr(self, "meta_data")
            and self.meta_data
            and isinstance(self.meta_data, dict)
        ):
            try:
                return AgentMetaData(**self.meta_data)
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
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate",
    )
    request_id: Optional[str] = None

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
