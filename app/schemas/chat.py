from datetime import datetime
from typing import List, Optional

from loguru import logger
from pydantic import BaseModel, field_serializer, model_validator

from app.models.message import MessageType, SenderType


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


class ChatSettingsBase(BaseModel):
    """聊天设置基础模型"""

    language: str = "en"
    voice_enabled: bool = True  # 个性化语音自动播放开关
    # keep_talking 字段已弃用，不再在 API 中暴露
    style_prompt: Optional[str] = None  # 风格提示词，仅订阅用户可设置
    premium_mode: bool = False  # 高级模式开关，仅订阅用户可设置


class ChatSettingsCreate(ChatSettingsBase):
    """创建聊天设置"""

    request_id: Optional[str] = None


class ChatSettingsUpdate(ChatSettingsBase):
    """更新聊天设置"""

    language: Optional[str] = None
    voice_enabled: Optional[bool] = None  # 个性化语音自动播放开关
    # keep_talking 字段已弃用，不再在 API 中暴露
    style_prompt: Optional[str] = None  # 风格提示词，仅订阅用户可设置
    premium_mode: Optional[bool] = None  # 高级模式开关，仅订阅用户可设置
    request_id: Optional[str] = None


class ChatSettingsInDB(ChatSettingsBase):
    """数据库中的聊天设置"""

    id: str
    user_id: str
    agent_id: str
    chat_id: str
    style_prompt: Optional[str] = None  # 风格提示词，仅订阅用户可设置
    premium_mode: bool = False  # 高级模式开关，仅订阅用户可设置
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

    pass


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
    agent_is_deleted: Optional[bool] = None
    agent_intro: Optional[str] = None
    agent_opening: Optional[str] = None
    agent_opening_audio_url: Optional[str] = None
    settings: Optional[ChatSettings] = None

    @field_serializer("agent_avatar")
    def serialize_agent_avatar(self, agent_avatar: Optional[str]) -> Optional[str]:
        """转换agent_avatar URL为CDN URL"""
        if not agent_avatar:
            return agent_avatar
        try:
            from app.services.image_transform_service import image_transform_service

            return image_transform_service.transform_mobile(agent_avatar)
        except Exception:
            return agent_avatar

    @field_serializer("agent_background")
    def serialize_agent_background(
        self, agent_background: Optional[str]
    ) -> Optional[str]:
        """转换agent_background URL为CDN URL"""
        if not agent_background:
            return agent_background
        try:
            from app.services.image_transform_service import image_transform_service

            return image_transform_service.transform_desktop(agent_background)
        except Exception:
            return agent_background


# OpenAI style message model
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    # DEPRECATED: Currently this parameter has no effect.
    stream: bool = False
    # DEPRECATED: Currently this parameter has no use.
    model: str = "chatbot"
    # DEPRECATED: Currently this parameter has no use.
    language: str = "zh"  # 添加语言字段，默认中文
    request_id: Optional[str] = None

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
    """清除消息请求"""

    message_id: Optional[int] = None  # 消息ID，清除该ID之后的所有消息
    timestamp: Optional[str] = None  # 时间戳，清除该时间之后的所有消息（ISO格式）
    request_id: Optional[str] = None

    class Config:
        # 确保至少有一个字段被提供
        json_schema_extra = {
            "example": {"message_id": 123, "timestamp": "2024-01-01T10:00:00Z"}
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


class ChatImageGenerationResponse(BaseModel):
    """聊天生图响应"""

    image_url: str
    image_metadata: dict
    prompt: str
    message_id: int
