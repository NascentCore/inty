from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

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
    voice_enabled: bool = True
    keep_talking: bool = True


class ChatSettingsCreate(ChatSettingsBase):
    """创建聊天设置"""
    pass


class ChatSettingsUpdate(ChatSettingsBase):
    """更新聊天设置"""
    language: Optional[str] = None
    voice_enabled: Optional[bool] = None
    keep_talking: Optional[bool] = None


class ChatSettingsInDB(ChatSettingsBase):
    """数据库中的聊天设置"""
    id: str
    user_id: str
    agent_id: str
    chat_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatSettings(ChatSettingsInDB):
    """聊天设置"""
    agent: Optional[dict] = None


class ChatBase(BaseModel):
    """聊天基础模型"""
    pass


class ChatCreate(ChatBase):
    """创建聊天"""
    pass


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
    messages: Optional[List[Message]] = None
    settings: Optional[ChatSettings] = None 