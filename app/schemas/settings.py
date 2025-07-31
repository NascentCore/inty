from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SettingsBase(BaseModel):
    """设置基础模型"""

    language: str = "en"
    voice_enabled: bool = True
    keep_talking: bool = True


class SettingsCreate(SettingsBase):
    """创建设置"""

    pass


class SettingsUpdate(BaseModel):
    """更新设置"""

    language: Optional[str] = None
    voice_enabled: Optional[bool] = None
    keep_talking: Optional[bool] = None


class SettingsInDB(SettingsBase):
    """数据库中的设置"""

    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Settings(SettingsInDB):
    """API 响应中的设置"""

    pass
