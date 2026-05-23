"""评测系统的Pydantic模型定义"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from app.models.evaluation import EvaluationStatus


class EvaluationSessionCreate(BaseModel):
    """创建评测会话的请求模型"""

    name: str = Field(
        ..., min_length=1, max_length=255, description="评测会话名称"
    )
    questions: List[str] = Field(..., min_items=1, description="测试问题列表")
    selected_agents: List[str] = Field(
        ..., min_items=1, description="选中的智能体ID列表"
    )
    scoring_model: str = Field(..., description="评分模型")
    scoring_criteria: Optional[str] = Field(None, description="评分标准")
    use_new_user_identity: bool = Field(False, description="是否使用新用户身份")
    config: Optional[Dict[str, Any]] = Field(None, description="其他配置参数")
    request_id: Optional[str] = None

    @validator("questions")
    def validate_questions(cls, v):
        """验证问题列表"""
        if not v:
            raise ValueError("Question list cannot be empty")

        # 去重
        unique_questions = []
        seen = set()
        for q in v:
            q_clean = q.strip()
            if q_clean and q_clean.lower() not in seen:
                unique_questions.append(q_clean)
                seen.add(q_clean.lower())

        if not unique_questions:
            raise ValueError("No valid questions found")

        if len(unique_questions) > 50:
            raise ValueError("Question count must not exceed 50")

        return unique_questions

    @validator("selected_agents")
    def validate_agents(cls, v):
        """验证智能体列表"""
        if not v:
            raise ValueError("At least one agent must be selected")

        if len(v) > 20:
            raise ValueError("Selected agents must not exceed 20")

        return list(set(v))  # 去重


class EvaluationSessionResponse(BaseModel):
    """评测会话响应模型"""

    id: str
    name: str
    creator_id: str
    status: EvaluationStatus
    questions: List[str]
    selected_agents: List[str]
    scoring_model: str
    scoring_criteria: Optional[str]
    use_new_user_identity: bool
    config: Optional[Dict[str, Any]]
    total_tests: int
    completed_tests: int
    success_rate: Optional[float]
    average_score: Optional[float]
    created_at: datetime
    updated_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class EvaluationResultResponse(BaseModel):
    """评测结果响应模型"""

    id: str
    session_id: str
    agent_id: str
    agent_name: Optional[str] = None
    question: str
    question_index: int
    agent_response: Optional[str]
    response_time: Optional[float]
    overall_score: Optional[float]
    detailed_scores: Optional[Dict[str, float]]
    scoring_reason: Optional[str]
    scoring_model_used: Optional[str]
    is_success: bool
    error_message: Optional[str]
    extra_data: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class EvaluationInteractionResponse(BaseModel):
    """评测交互记录响应模型"""

    id: str
    session_id: str
    result_id: str
    chat_id: Optional[str]
    user_input: Optional[str]
    agent_response: Optional[str]
    interaction_order: Optional[int]
    user_identity: Optional[Dict[str, Any]]
    response_metadata: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class EvaluationSessionDetail(EvaluationSessionResponse):
    """评测会话详细信息（包含结果）"""

    results: List[EvaluationResultResponse] = Field(default_factory=list)
    interactions: List[EvaluationInteractionResponse] = Field(
        default_factory=list
    )


class EvaluationTemplateCreate(BaseModel):
    """创建评测模板的请求模型"""

    name: str = Field(..., min_length=1, max_length=255, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    questions: List[str] = Field(..., min_items=1, description="问题列表")
    default_scoring_criteria: Optional[str] = Field(
        None, description="默认评分标准"
    )
    recommended_models: Optional[List[str]] = Field(
        None, description="推荐的评分模型"
    )
    config: Optional[Dict[str, Any]] = Field(None, description="模板配置")
    tags: Optional[List[str]] = Field(None, description="标签")
    is_public: bool = Field(False, description="是否公开")
    request_id: Optional[str] = None


class EvaluationTemplateResponse(BaseModel):
    """评测模板响应模型"""

    id: str
    name: str
    description: Optional[str]
    creator_id: str
    questions: List[str]
    default_scoring_criteria: Optional[str]
    recommended_models: Optional[List[str]]
    config: Optional[Dict[str, Any]]
    tags: Optional[List[str]]
    usage_count: int
    is_public: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class QuestionFileUpload(BaseModel):
    """问题文件上传结果"""

    questions: List[str]
    total_count: int
    valid_count: int
    duplicates_removed: int
    warnings: List[str] = Field(default_factory=list)


class ScoringModelInfo(BaseModel):
    """评分模型信息"""

    id: str
    name: str
    description: Optional[str]
    context_length: Optional[int]
    provider: Optional[str]


class EvaluationStats(BaseModel):
    """评测统计信息"""

    total_sessions: int
    completed_sessions: int
    running_sessions: int
    failed_sessions: int
    average_score: Optional[float]
    success_rate: Optional[float]
    total_tests: int
    total_agents_tested: int


class WebSocketMessage(BaseModel):
    """WebSocket消息格式"""

    type: str = Field(..., description="消息类型")
    session_id: str = Field(..., description="会话ID")
    data: Optional[Dict[str, Any]] = Field(None, description="消息数据")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="时间戳"
    )


class EvaluationSessionUpdate(BaseModel):
    """更新评测会话"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    scoring_criteria: Optional[str] = None
    request_id: Optional[str] = None


class BatchEvaluationRequest(BaseModel):
    """批量评测请求"""

    template_id: Optional[str] = Field(None, description="使用的模板ID")
    sessions: List[EvaluationSessionCreate] = Field(
        ..., min_items=1, max_items=5, description="评测会话列表"
    )
    request_id: Optional[str] = None

    @validator("sessions")
    def validate_sessions(cls, v):
        if len(v) > 5:
            raise ValueError("Batch evaluation supports up to 5 sessions")
        return v


class EvaluationComparison(BaseModel):
    """评测对比结果"""

    agents: List[str]
    questions: List[str]
    results: Dict[str, Dict[str, Any]]  # agent_id -> question_index -> result
    summary: Dict[str, Any]


class EvaluationExportRequest(BaseModel):
    """评测结果导出请求"""

    session_ids: List[str] = Field(
        ..., min_items=1, description="要导出的会话ID列表"
    )
    format: str = Field(
        "csv", pattern="^(csv|json|xlsx)$", description="导出格式"
    )
    include_interactions: bool = Field(False, description="是否包含交互记录")
    include_metadata: bool = Field(False, description="是否包含元数据")
    request_id: Optional[str] = None


class SurpriseSnapUnlockRequest(BaseModel):
    """免费用户用 credit 解锁 Surprise Snap 消息的请求（扣费在 app 端，后端仅记录解锁状态）。"""

    message_id: int = Field(..., description="要解锁的 surprise_snap 消息 ID")
