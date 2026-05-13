import sqlalchemy
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.models.base import Base


class VoiceCache(Base):
    """语音缓存表"""

    __tablename__ = "voice_cache"

    id = Column(String, primary_key=True, index=True)
    content_hash = Column(String, unique=True, index=True)  # 内容哈希值
    text_content = Column(Text, nullable=False)  # 原始文本内容
    voice_id = Column(String, nullable=False)  # 语音ID
    model = Column(String, nullable=False)  # 模型名称
    language = Column(String, nullable=False)  # 语言
    audio_url = Column(String, nullable=False)  # 音频文件URL
    # nullable=True 保持兼容性
    # TODO：填充 duration 数值到数据库，并设置 nullable=False
    duration = Column(Float, nullable=True, default=0.0)  # 音频时长（秒）
    file_size = Column(Integer, default=0)  # 文件大小（字节）
    hit_count = Column(Integer, default=0)  # 缓存命中次数
    last_accessed = Column(
        DateTime(timezone=True), server_default=sqlalchemy.text("now()")
    )
    created_at = Column(
        DateTime(timezone=True), server_default=sqlalchemy.text("now()")
    )
    is_active = Column(Boolean, default=True)  # 是否激活
