from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.message import MessageType, SenderType


class MessageBase(BaseModel):
    """消息基础模型"""

    content: str
    type: MessageType = MessageType.TEXT
    sender_type: SenderType


class MessageCreate(MessageBase):
    """创建消息"""

    pass


class MessageUpdate(BaseModel):
    """更新消息"""

    content: Optional[str] = None
    type: Optional[MessageType] = None
    sender_type: Optional[SenderType] = None


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

    pass


class ChatSettingsUpdate(ChatSettingsBase):
    """更新聊天设置"""

    language: Optional[str] = None
    voice_enabled: Optional[bool] = None  # 个性化语音自动播放开关
    # keep_talking 字段已弃用，不再在 API 中暴露
    style_prompt: Optional[str] = None  # 风格提示词，仅订阅用户可设置
    premium_mode: Optional[bool] = None  # 高级模式开关，仅订阅用户可设置


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


class ChatUpdate(ChatBase):
    """更新聊天"""

    pass


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
    agent_is_deleted: Optional[bool] = None
    settings: Optional[ChatSettings] = None


class ChatCompletionRequest(BaseModel):
    """聊天完成请求模型"""

    messages: List[dict]
    stream: bool = False
    language: str = "zh"  # 语言


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


