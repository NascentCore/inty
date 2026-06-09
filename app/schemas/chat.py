import enum
from datetime import datetime
from typing import Annotated, Any, Dict, List, Literal, Optional

from loguru import logger
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    model_validator,
)

from app.schemas.biz_action import BizAction
from app.core.agent.prompt_template import (
    has_template_variable,
    render_prompt_jinja2_template,
)


class MessageType(str, enum.Enum):
    """消息类型"""

    TEXT = "TEXT"
    VOICE = "VOICE"
    IMAGE = "IMAGE"


class SenderType(str, enum.Enum):
    """发送者类型"""

    USER = "USER"
    AI = "AI"


class MessageBase(BaseModel):
    """消息基础模型"""

    content: str
    type: MessageType = MessageType.TEXT
    sender_type: SenderType


class MessageCreate(MessageBase):
    """创建消息"""

    request_id: Optional[str] = None


class MessageUpdate(BaseModel):
    """更新消息"""

    content: Optional[str] = None
    type: Optional[MessageType] = None
    sender_type: Optional[SenderType] = None
    request_id: Optional[str] = None


class MessageInDB(MessageBase):
    """数据库中的消息"""

    id: str
    sender_id: str
    agent_id: str
    chat_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class Message(MessageInDB):
    """消息"""

    sender: Optional[dict] = None


class MessageList(BaseModel):
    """消息列表"""

    total: int
    page: int
    page_size: int
    items: List[Message]


class ChatModeOption(BaseModel):
    """Chat mode option for list API (id, short_name, name, description)."""

    id: str
    short_name: str = ""
    name: str = ""
    description: str = ""


class ChatSettingsBase(BaseModel):
    """聊天设置基础模型。

    当前不包含「选择模型」；模型选择仅由角色配置与订阅层决定，见 agent / model_selection。
    """

    language: str = "en"
    voice_enabled: bool = True  # 个性化语音自动播放开关
    voice_id: Optional[str] = (
        None  # Per-chat selected voice id (google/* for MVP)
    )
    # keep_talking 字段已弃用，不再在 API 中暴露
    style_prompt: Optional[str] = None  # 风格提示词，仅订阅用户可设置
    premium_mode: bool = False  # 高级模式开关，仅订阅用户可设置
    chat_mode: Optional[str] = (
        None  # User-selected chat mode id; null = use agent default
    )


class ChatSettingsCreate(ChatSettingsBase):
    """创建聊天设置"""

    request_id: Optional[str] = None


class ChatSettingsUpdate(ChatSettingsBase):
    """更新聊天设置"""

    language: Optional[str] = None
    voice_enabled: Optional[bool] = None  # 个性化语音自动播放开关
    voice_id: Optional[str] = (
        None  # Per-chat selected voice id (google/* for MVP)
    )
    # keep_talking 字段已弃用，不再在 API 中暴露
    style_prompt: Optional[str] = None  # 风格提示词，仅订阅用户可设置
    premium_mode: Optional[bool] = None  # 高级模式开关，仅订阅用户可设置
    chat_mode: Optional[str] = None  # User-selected chat mode id
    request_id: Optional[str] = None


class ChatSettingsInDB(ChatSettingsBase):
    """数据库中的聊天设置"""

    id: str
    user_id: str
    agent_id: str
    chat_id: str
    style_prompt: Optional[str] = None  # 风格提示词，仅订阅用户可设置
    premium_mode: bool = False  # 高级模式开关，仅订阅用户可设置
    chat_mode: Optional[str] = None  # User-selected chat mode id
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        # 当设置为 True 时，Pydantic 可以从具有属性的对象（如 SQLAlchemy 模型实例）创建模型实例
        # 允许从 ORM 对象直接转换为 Pydantic 模型，而不需要手动映射每个字段
        # 在 FastAPI 中，通常需要将数据库模型转换为 API 响应模型
        # 例如，从 SQLAlchemy 模型创建 Pydantic 模型
        # class UserModel(Base):
        #     __tablename__ = "users"
        #     id = Column(Integer, primary_key=True)
        #     name = Column(String)
        #     email = Column(String)
        # class UserSchema(BaseModel):
        #     model_config = ConfigDict(from_attributes=True)
        #     id: int
        #     name: str
        #     email: str
        # # 可以直接从 SQLAlchemy 对象创建 Pydantic 模型
        # user_obj = session.query(UserModel).first()
        # user_schema = UserSchema.model_validate(user_obj)  # 自动映射属性
        from_attributes = True


class ChatSettings(ChatSettingsInDB):
    """聊天设置"""

    available_chat_modes: Optional[List["ChatModeOption"]] = (
        None  # Only set when agent default is in user-facing modes
    )


class ChatBase(BaseModel):
    """聊天基础模型"""

    pass


class ChatCreate(ChatBase):
    """创建聊天"""

    agent_id: str
    request_id: Optional[str] = None


class ChatUpdate(ChatBase):
    """更新聊天"""

    request_id: Optional[str] = None


class ChatInDB(ChatBase):
    """数据库中的聊天"""

    id: str
    user_id: str
    agent_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Chat(ChatInDB):
    """聊天"""

    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    agent_name: Optional[str] = None
    agent_avatar: Optional[str] = None
    agent_background: Optional[str] = None
    agent_background_animated: Optional[str] = None
    agent_extensions: Optional[Dict[str, Any]] = None
    agent_is_deleted: Optional[bool] = None
    agent_intro: Optional[str] = None
    agent_opening: Optional[str] = None
    agent_opening_audio_url: Optional[str] = None
    settings: Optional[ChatSettings] = None

    @field_serializer("agent_avatar")
    def serialize_agent_avatar(
        self, agent_avatar: Optional[str]
    ) -> Optional[str]:
        """转换agent_avatar URL为CDN URL，支持基于extension裁切数据的avatar生成"""
        try:
            from app.services.image_transform_service import (
                image_transform_service,
            )

            # 优先检查是否存在裁切数据，如果存在则使用裁切数据而不是独立的avatar
            if (
                self.agent_background
                and self.agent_extensions
                and isinstance(self.agent_extensions, dict)
                and "avatar_crop" in self.agent_extensions
            ):

                avatar_crop_data = self.agent_extensions["avatar_crop"]

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
                        self.agent_background, cropped_area
                    )

            # 如果没有裁切数据但有独立的avatar，使用常规转换
            if agent_avatar:
                return image_transform_service.transform_mobile(agent_avatar)

            return agent_avatar

        except (ImportError, AttributeError, TypeError, ValueError) as e:
            logger.bind(
                chat_id=getattr(self, "id", "unknown"),
                field="agent_avatar",
            ).warning("Failed to serialize chat image URL: {}", e)
            return agent_avatar

    @field_serializer("agent_background")
    def serialize_agent_background(
        self, agent_background: Optional[str]
    ) -> Optional[str]:
        """转换agent_background URL为CDN URL"""
        if not agent_background:
            return agent_background
        try:
            from app.services.image_transform_service import (
                image_transform_service,
            )

            return image_transform_service.transform_desktop(agent_background)
        except (ImportError, AttributeError, TypeError, ValueError) as e:
            logger.bind(
                chat_id=getattr(self, "id", "unknown"),
                field="agent_background",
            ).warning("Failed to serialize chat image URL: {}", e)
            return agent_background

    @field_serializer("agent_background_animated")
    def serialize_agent_background_animated(
        self, agent_background_animated: Optional[str]
    ) -> Optional[str]:
        """转换agent_background_animated URL为CDN URL"""
        if not agent_background_animated:
            return agent_background_animated
        try:
            from app.services.image_transform_service import (
                image_transform_service,
            )

            return image_transform_service.transform_desktop(
                agent_background_animated
            )
        except (ImportError, AttributeError, TypeError, ValueError) as e:
            logger.bind(
                chat_id=getattr(self, "id", "unknown"),
                field="agent_background_animated",
            ).warning("Failed to serialize chat image URL: {}", e)
            return agent_background_animated

    @field_serializer("agent_intro")
    def serialize_agent_intro(
        self, agent_intro: Optional[str]
    ) -> Optional[str]:
        """渲染 agent_intro 中的模板变量，避免客户端展示原始 {{ char }}。"""
        if not agent_intro or not has_template_variable(agent_intro):
            return agent_intro
        return render_prompt_jinja2_template(
            agent_intro,
            char=self.agent_name or "IntelliMate",
            user="you",
        )

    @field_serializer("agent_opening")
    def serialize_agent_opening(
        self, agent_opening: Optional[str]
    ) -> Optional[str]:
        """渲染 agent_opening 中的模板变量，保证接口返回可直接展示。"""
        if not agent_opening or not has_template_variable(agent_opening):
            return agent_opening
        return render_prompt_jinja2_template(
            agent_opening,
            char=self.agent_name or "IntelliMate",
            user="you",
        )


# OpenAI style message model
class ChatMessageTextContentPart(BaseModel):
    type: Literal["text"]
    text: str = Field(min_length=1)


class ChatMessageImageUrlData(BaseModel):
    url: str = Field(min_length=1)


class ChatMessageImageContentPart(BaseModel):
    type: Literal["image_url"]
    image_url: ChatMessageImageUrlData


ChatMessageContentPart = Annotated[
    ChatMessageTextContentPart | ChatMessageImageContentPart,
    Field(discriminator="type"),
]


class CompanionChatTurnMessageType(str, enum.Enum):
    """Turn category for companion chat completion requests (normal user turns)."""

    USER_MESSAGE = "USER_MESSAGE"


# TODO(companion-multimodal-user-turn): Phase 1 wire DTO — WS/HTTP map ``ChatMessage.content``
# https://github.com/NascentCore/inty/issues/3293
# parts (``image_url``) to harness ``CompanionUserTurnInput``; companion harness keeps its
# own immutable in-process type (see ``companion/user_turn_input.py``).
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str | List[ChatMessageContentPart]

    def to_model_content(self) -> str | List[Dict[str, Any]]:
        if isinstance(self.content, str):
            return self.content
        return [part.model_dump(exclude_none=True) for part in self.content]

    def extract_text_content(self) -> str:
        if isinstance(self.content, str):
            return self.content
        text_parts = [
            part.text.strip()
            for part in self.content
            if isinstance(part, ChatMessageTextContentPart)
            and part.text.strip()
        ]
        return "\n".join(text_parts)

    def has_image_content_part(self) -> bool:
        if isinstance(self.content, str):
            return False
        return any(
            isinstance(part, ChatMessageImageContentPart)
            for part in self.content
        )


class UserTimeContext(BaseModel):
    """用户时间上下文（来自客户端）"""

    local_time: Optional[str] = None  # ISO 8601 或可读时间字符串
    timezone: Optional[str] = None  # IANA 时区名称，如 Asia/Shanghai
    utc_offset_minutes: Optional[int] = (
        None  # UTC 偏移分钟数，如 480 表示 UTC+8
    )


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    messages: List[ChatMessage]
    # DEPRECATED: Currently this parameter has no effect.
    stream: bool = False
    # DEPRECATED: Currently this parameter has no use.
    model: str = "chatbot"
    # DEPRECATED: Currently this parameter has no use.
    language: str = "zh"  # 添加语言字段，默认中文
    request_id: Optional[str] = None
    user_time_context: Optional[UserTimeContext] = Field(
        default=None, alias="time_context"
    )  # 可选的用户时间上下文
    # TODO：目前还在实施中 https://github.com/NascentCore/inty/issues/1364
    message_id: Optional[str] = (
        None  # Required for WebSocket companion: RFC4122 UUID, used as transcript user_msg_uuid.
    )
    local_id: Optional[str] = Field(
        default=None,
        alias="localId",
        description="Client-generated id for optimistic UI; stored in chat_history.meta_data",
    )
    target_imate_id: Optional[str] = None
    message_type: CompanionChatTurnMessageType = Field(
        default=CompanionChatTurnMessageType.USER_MESSAGE,
        alias="messageType",
        description="Turn kind; greeting uses WebSocket ``user_signed_on`` with ``message_id``.",
    )

    @model_validator(mode="after")
    def check_deprecated_fields(self) -> "ChatCompletionRequest":
        if self.stream:
            logger.warning("DEPRECATED: 'stream' parameter has no effect")
        if self.model != "chatbot":
            logger.warning("DEPRECATED: 'model' parameter has no use")
        if self.language != "zh":
            logger.warning("DEPRECATED: 'language' parameter has no use")
        return self


class ChatCompletionResponse(BaseModel):
    """聊天完成响应模型"""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    # 无实际效果数据，仅用于测试 Kotlin 客户端代码接收到了这个字段（Kotlin 客户端类型代码定义正确）。
    business_actions: List[BizAction] = Field(default_factory=list)
    source_imate_id: Optional[str] = None
    choices: List[dict]
    usage: dict


class ChatDeletionSummary(BaseModel):
    """聊天删除结果摘要"""

    chats_deleted: int
    messages_deleted: int
    agent_id: str
    user_id: str
    status: str


class ChatDeletionResponse(BaseModel):
    """聊天删除响应"""

    success: bool
    message: str
    data: ChatDeletionSummary


class ClearMessagesRequest(BaseModel):
    """
    清除消息请求（软删除）

    支持三种模式：
    1. 提供 message_id：清除该ID及其之后的所有消息
    2. 提供 timestamp：清除该时间之后的所有消息
    3. 都不提供：清除全部消息

    注意：message_id 和 timestamp 不能同时提供
    """

    message_id: Optional[int] = None  # 消息ID，清除该ID及其之后的所有消息
    timestamp: Optional[str] = (
        None  # 时间戳，清除该时间之后的所有消息（ISO格式）
    )
    request_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "examples": [
                {"message_id": 123},
                {"timestamp": "2024-01-01T10:00:00Z"},
                {},
            ]
        }


class ClearMessagesResponse(BaseModel):
    """清除消息响应"""

    success: bool
    message: str
    deleted_count: int
    target_message: Optional[dict] = None  # 目标消息信息（当使用message_id时）
    deleted_time_range: Optional[dict] = None  # 删除的时间范围
    cutoff_timestamp: Optional[str] = None  # 截止时间戳（当使用timestamp时）


class ChatImageGenerationRequest(BaseModel):
    """聊天生图请求 - 基于已有消息生成图片"""

    message_id: int  # 必填：要生成图片的消息ID
    history_count: Optional[int] = None
    request_id: Optional[str] = None
    # TODO: 移除 model 参数（当前按订阅状态选择模型，请求中的 model 未被使用）
    model: Optional[str] = None


class ChatImageGenerationResponse(BaseModel):
    """聊天生图响应"""

    image_url: str
    image_metadata: dict
    prompt: str
    message_id: int
    model: Optional[str] = None  # 使用的生图模型
    generation_time_ms: Optional[int] = None  # 模型调用耗时（毫秒）
    model_fallback_due_to_429: Optional[bool] = (
        None  # 是否因 429 使用了备用模型
    )


class ChatMusicGenerationRequest(BaseModel):
    """聊天生音乐请求 - 基于已有消息生成音乐"""

    message_id: int  # 必填：要生成音乐的消息ID
    history_count: Optional[int] = None
    request_id: Optional[str] = None
    model: Optional[str] = None  # 允许请求方显式指定模型 ID（可选）


class ChatMusicGenerationResponse(BaseModel):
    """聊天生音乐响应"""

    audio_url: str
    audio_metadata: dict
    prompt: str
    message_id: int
    model: Optional[str] = None
    generation_time_ms: Optional[int] = None


class MessageVoteRequest(BaseModel):
    """消息投票请求"""

    agent_id: str
    message_id: int
    vote: Optional[str] = None  # "like" | "dislike" | null
    request_id: Optional[str] = None


class SurpriseSnapUnlockRequest(BaseModel):
    """免费用户用 credit 解锁 Surprise Snap 消息（扣费在 app 端，后端仅记录解锁状态）。"""

    message_id: int = Field(..., description="要解锁的 surprise_snap 消息 ID")
