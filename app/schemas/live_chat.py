"""
实时语音通话相关的 schema 定义
CREATED_BY_AGENT
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LiveChatStatus(str, Enum):
    """实时语音通话会话状态"""

    CONNECTING = "connecting"  # 正在连接
    CONNECTED = "connected"  # 已连接
    SPEAKING = "speaking"  # AI 正在说话
    LISTENING = "listening"  # 正在监听用户
    DISCONNECTED = "disconnected"  # 已断开
    ERROR = "error"  # 错误状态


class LiveChatMessageType(str, Enum):
    """WebSocket 消息类型"""

    # 上行消息类型
    AUDIO = "audio"  # 音频数据 (Base64 编码的 PCM)
    TEXT = "text"  # 文本输入
    CONFIG = "config"  # 会话配置
    END = "end"  # 结束通话

    # 下行消息类型
    AUDIO_RESPONSE = "audio_response"  # AI 音频响应
    TRANSCRIPT = "transcript"  # AI 回复的转录文本
    USER_TRANSCRIPT = "user_transcript"  # 用户语音的转录文本
    STATUS = "status"  # 会话状态更新
    ERROR = "error"  # 错误消息


class LiveChatConfig(BaseModel):
    """实时语音通话配置"""

    save_history: bool = Field(
        default=True,
        description="是否将语音对话保存到聊天历史",
    )
    voice_id: Optional[str] = Field(
        default=None,
        description="指定 AI 语音 ID，为空则使用角色默认语音或系统默认语音",
    )


class LiveChatMessage(BaseModel):
    """WebSocket 消息基础结构"""

    type: LiveChatMessageType = Field(..., description="消息类型")
    data: Optional[str] = Field(default=None, description="消息数据")
    timestamp: Optional[float] = Field(default=None, description="时间戳（毫秒）")


class LiveChatAudioMessage(BaseModel):
    """音频消息"""

    type: LiveChatMessageType = Field(
        default=LiveChatMessageType.AUDIO,
        description="消息类型",
    )
    data: str = Field(..., description="Base64 编码的 PCM 音频数据")
    sample_rate: int = Field(default=16000, description="采样率")


class LiveChatTextMessage(BaseModel):
    """文本消息"""

    type: LiveChatMessageType = Field(
        default=LiveChatMessageType.TEXT,
        description="消息类型",
    )
    data: str = Field(..., description="文本内容")


class LiveChatConfigMessage(BaseModel):
    """配置消息"""

    type: LiveChatMessageType = Field(
        default=LiveChatMessageType.CONFIG,
        description="消息类型",
    )
    config: LiveChatConfig = Field(..., description="会话配置")


class LiveChatStatusMessage(BaseModel):
    """状态消息（下行）"""

    type: LiveChatMessageType = Field(
        default=LiveChatMessageType.STATUS,
        description="消息类型",
    )
    status: LiveChatStatus = Field(..., description="会话状态")
    message: Optional[str] = Field(default=None, description="状态描述")


class LiveChatTranscriptMessage(BaseModel):
    """转录消息（下行）"""

    type: LiveChatMessageType = Field(..., description="消息类型")
    text: str = Field(..., description="转录文本")
    is_final: bool = Field(default=True, description="是否是最终转录结果")


class LiveChatAudioResponseMessage(BaseModel):
    """AI 音频响应消息（下行）"""

    type: LiveChatMessageType = Field(
        default=LiveChatMessageType.AUDIO_RESPONSE,
        description="消息类型",
    )
    data: str = Field(..., description="Base64 编码的 PCM 音频数据")
    sample_rate: int = Field(default=24000, description="采样率")


class LiveChatErrorMessage(BaseModel):
    """错误消息（下行）"""

    type: LiveChatMessageType = Field(
        default=LiveChatMessageType.ERROR,
        description="消息类型",
    )
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误描述")

