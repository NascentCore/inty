from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field

from app.models.system_settings import SettingType, SettingCategory


class SystemSettingBase(BaseModel):
    """系统配置基础模型"""
    key: str = Field(..., description="配置键名")
    value: str = Field(..., description="配置值")
    value_type: SettingType = Field(..., description="值类型")
    category: SettingCategory = Field(..., description="配置分类")
    description: Optional[str] = Field(None, description="配置描述")
    default_value: Optional[str] = Field(None, description="默认值")
    is_system: bool = Field(False, description="是否为系统内置配置")
    is_readonly: bool = Field(False, description="是否只读")


class SystemSettingCreate(SystemSettingBase):
    """创建系统配置"""
    pass


class SystemSettingUpdate(BaseModel):
    """更新系统配置"""
    value: str = Field(..., description="配置值")
    description: Optional[str] = Field(None, description="配置描述")


class SystemSetting(SystemSettingBase):
    """系统配置响应模型"""
    updated_by: Optional[str] = Field(None, description="最后更新者ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    parsed_value: Any = Field(..., description="解析后的值")

    class Config:
        from_attributes = True


class SystemSettingsListResponse(BaseModel):
    """系统配置列表响应"""
    total: int = Field(..., description="总数量")
    items: List[SystemSetting] = Field(..., description="配置项列表")


class SystemSettingUpdateRequest(BaseModel):
    """系统配置更新请求"""
    value: str = Field(..., description="新的配置值")


class FreeUserLimitsResponse(BaseModel):
    """免费用户限制响应"""
    background_generation_limit: int = Field(..., description="每日背景图生成限制")
    chat_total_limit: int = Field(..., description="总聊天次数限制")
    agent_creation_limit: int = Field(..., description="Agent创建数量限制")