from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class CharacterCardSpec(str, Enum):
    """角色卡规范版本"""
    V1 = "chara_card_v1"
    V2 = "chara_card_v2"


class CharacterBookEntry(BaseModel):
    """角色书条目"""
    keys: List[str] = Field(..., description="触发关键词")
    content: str = Field(..., description="条目内容")
    extensions: Dict[str, Any] = Field(default_factory=dict, description="扩展数据")
    enabled: bool = Field(True, description="是否启用")
    insertion_order: int = Field(100, description="插入顺序")
    constant: bool = Field(False, description="是否常驻")
    selective: bool = Field(False, description="是否选择性")
    secondary_keys: List[str] = Field(default_factory=list, description="次要关键词")
    position: str = Field("after_char", description="插入位置")
    
    @validator('keys')
    def validate_keys(cls, v):
        if not v:
            raise ValueError("keys cannot be empty")
        return v


class CharacterBook(BaseModel):
    """角色书"""
    name: Optional[str] = Field(None, description="角色书名称")
    description: Optional[str] = Field(None, description="角色书描述")
    scan_depth: Optional[int] = Field(100, description="扫描深度")
    token_budget: Optional[int] = Field(512, description="令牌预算")
    recursive_scanning: Optional[bool] = Field(False, description="递归扫描")
    extensions: Dict[str, Any] = Field(default_factory=dict, description="扩展数据")
    entries: List[CharacterBookEntry] = Field(default_factory=list, description="条目列表")


class CharacterCardDataV2(BaseModel):
    """角色卡V2数据模型"""
    name: str = Field(..., description="角色名称")
    description: str = Field("", description="角色描述")
    personality: str = Field("", description="性格特征")
    scenario: str = Field("", description="场景设定")
    first_mes: str = Field("", description="第一条消息")
    mes_example: str = Field("", description="对话示例")
    
    # V2新增字段
    creator_notes: str = Field("", description="创建者备注")
    system_prompt: str = Field("", description="系统提示词")
    post_history_instructions: str = Field("", description="历史后指令")
    alternate_greetings: List[str] = Field(default_factory=list, description="替代问候语")
    character_book: Optional[CharacterBook] = Field(None, description="角色书")
    tags: List[str] = Field(default_factory=list, description="标签")
    creator: str = Field("", description="创建者")
    character_version: str = Field("1.0", description="角色版本")
    extensions: Dict[str, Any] = Field(default_factory=dict, description="扩展数据")


class CharacterCardV2(BaseModel):
    """角色卡V2完整模型"""
    spec: CharacterCardSpec = Field(CharacterCardSpec.V2, description="规范版本")
    spec_version: str = Field("2.0", description="规范版本号")
    data: CharacterCardDataV2 = Field(..., description="角色卡数据")
    
    @validator('spec')
    def validate_spec(cls, v):
        if v != CharacterCardSpec.V2:
            raise ValueError("Only chara_card_v2 is supported")
        return v
    
    @validator('spec_version')
    def validate_spec_version(cls, v):
        if v != "2.0":
            raise ValueError("Only spec version 2.0 is supported")
        return v


class CharacterCardImportRequest(BaseModel):
    """角色卡导入请求"""
    card_data: Union[CharacterCardV2, Dict[str, Any]] = Field(..., description="角色卡数据")
    override_existing: bool = Field(False, description="是否覆盖现有同名角色")
    import_character_book: bool = Field(True, description="是否导入角色书")
    import_alternate_greetings: bool = Field(True, description="是否导入替代问候语")
    
    class Config:
        json_schema_extra = {
            "example": {
                "card_data": {
                    "spec": "chara_card_v2",
                    "spec_version": "2.0",
                    "data": {
                        "name": "Alice",
                        "description": "A helpful AI assistant",
                        "personality": "Friendly and helpful",
                        "scenario": "Modern office setting",
                        "first_mes": "Hello! How can I help you today?",
                        "mes_example": "<START>\nUser: Hi\nAlice: Hello! How can I assist you?\n<END>",
                        "creator_notes": "This is a test character",
                        "system_prompt": "You are Alice, a helpful AI assistant.",
                        "tags": ["assistant", "helpful"],
                        "creator": "Test User",
                        "character_version": "1.0"
                    }
                },
                "override_existing": False,
                "import_character_book": True,
                "import_alternate_greetings": True
            }
        }


class CharacterCardImportResponse(BaseModel):
    """角色卡导入响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    agent_id: Optional[str] = Field(None, description="创建的Agent ID")
    imported_features: List[str] = Field(default_factory=list, description="导入的功能列表")
    warnings: List[str] = Field(default_factory=list, description="警告信息")


class CharacterCardExportRequest(BaseModel):
    """角色卡导出请求"""
    agent_id: str = Field(..., description="Agent ID")
    include_character_book: bool = Field(True, description="是否包含角色书")
    include_alternate_greetings: bool = Field(True, description="是否包含替代问候语")
    include_extensions: bool = Field(True, description="是否包含扩展数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "agent_123",
                "include_character_book": True,
                "include_alternate_greetings": True,
                "include_extensions": True
            }
        }


class CharacterCardValidationError(BaseModel):
    """角色卡验证错误"""
    field: str = Field(..., description="错误字段")
    message: str = Field(..., description="错误消息")
    code: str = Field(..., description="错误代码")


class CharacterCardValidationResponse(BaseModel):
    """角色卡验证响应"""
    is_valid: bool = Field(..., description="是否有效")
    errors: List[CharacterCardValidationError] = Field(default_factory=list, description="验证错误")
    warnings: List[str] = Field(default_factory=list, description="警告信息")
    supported_features: List[str] = Field(default_factory=list, description="支持的功能")