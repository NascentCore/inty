import enum
import uuid

import sqlalchemy as sa
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class EvaluationStatus(str, enum.Enum):
    """评测状态"""

    PENDING = "PENDING"  # 待开始
    RUNNING = "RUNNING"  # 进行中
    COMPLETED = "COMPLETED"  # 已完成
    FAILED = "FAILED"  # 失败
    CANCELLED = "CANCELLED"  # 已取消


class EvaluationSession(Base):
    """评测会话模型"""

    __tablename__ = "evaluation_sessions"

    id = Column(
        String, primary_key=True, index=True, default=lambda: str(uuid.uuid4())
    )
    name = Column(String(255), nullable=False, comment="评测会话名称")
    creator_id = Column(
        String, ForeignKey("users.id"), nullable=False, comment="创建者ID"
    )
    status = Column(
        Enum(EvaluationStatus, name="evaluation_status"),
        default=EvaluationStatus.PENDING,
        comment="评测状态",
    )

    # 评测配置
    questions = Column(JSON, nullable=False, comment="测试问题列表")
    selected_agents = Column(JSON, nullable=False, comment="选中的智能体ID列表")
    scoring_model = Column(String(255), nullable=False, comment="评分模型")
    scoring_criteria = Column(Text, comment="评分标准")
    use_new_user_identity = Column(
        Boolean, default=False, comment="是否使用新用户身份"
    )

    # 配置参数
    config = Column(JSON, comment="其他配置参数")

    # 统计信息
    total_tests = Column(Integer, default=0, comment="总测试数量")
    completed_tests = Column(Integer, default=0, comment="已完成测试数量")
    success_rate = Column(Float, comment="成功率")
    average_score = Column(Float, comment="平均分数")

    # 时间戳
    created_at = Column(
        DateTime(timezone=True), server_default=sa.text("now()")
    )
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text("now()"))
    started_at = Column(DateTime(timezone=True), comment="开始时间")
    completed_at = Column(DateTime(timezone=True), comment="完成时间")

    # 关系
    creator = relationship("User", back_populates="evaluation_sessions")
    results = relationship(
        "EvaluationResult",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    interactions = relationship(
        "EvaluationInteraction",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class EvaluationResult(Base):
    """评测结果模型"""

    __tablename__ = "evaluation_results"

    id = Column(
        String, primary_key=True, index=True, default=lambda: str(uuid.uuid4())
    )
    session_id = Column(
        String, ForeignKey("evaluation_sessions.id"), nullable=False
    )
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    agent_name = Column(
        String(255), comment="智能体名称（冗余字段，提高查询效率）"
    )
    question = Column(Text, nullable=False, comment="测试问题")
    question_index = Column(Integer, nullable=False, comment="问题序号")

    # 对话结果
    agent_response = Column(Text, comment="智能体回复")
    response_time = Column(Float, comment="回复时间(秒)")

    # 评分结果
    overall_score = Column(Float, comment="总分")
    detailed_scores = Column(JSON, comment="详细评分 {dimension: score}")
    scoring_reason = Column(Text, comment="评分理由")
    scoring_model_used = Column(String(255), comment="使用的评分模型")

    # 状态
    is_success = Column(Boolean, default=True, comment="是否成功完成")
    error_message = Column(Text, comment="错误信息")

    # 元数据
    extra_data = Column(JSON, comment="其他元数据")

    # 时间戳
    created_at = Column(
        DateTime(timezone=True), server_default=sa.text("now()")
    )
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text("now()"))

    # 关系
    session = relationship("EvaluationSession", back_populates="results")
    agent = relationship("Agent")
    interactions = relationship(
        "EvaluationInteraction", back_populates="result"
    )


class EvaluationInteraction(Base):
    """评测交互记录模型 - 记录完整的对话过程"""

    __tablename__ = "evaluation_interactions"

    id = Column(
        String, primary_key=True, index=True, default=lambda: str(uuid.uuid4())
    )
    session_id = Column(
        String, ForeignKey("evaluation_sessions.id"), nullable=False
    )
    result_id = Column(
        String, ForeignKey("evaluation_results.id"), nullable=False
    )
    chat_id = Column(
        String,
        ForeignKey("chats.id"),
        nullable=True,
        comment="关联的聊天会话ID",
    )

    # 交互信息
    user_input = Column(Text, comment="用户输入")
    agent_response = Column(Text, comment="智能体回复")
    interaction_order = Column(Integer, comment="交互顺序")

    # 技术信息
    user_identity = Column(JSON, comment="用户身份信息")
    response_metadata = Column(JSON, comment="回复元数据")

    # 时间戳
    created_at = Column(
        DateTime(timezone=True), server_default=sa.text("now()")
    )

    # 关系
    session = relationship("EvaluationSession", back_populates="interactions")
    result = relationship("EvaluationResult", back_populates="interactions")
    chat = relationship("Chat")


class EvaluationTemplate(Base):
    """评测模板模型"""

    __tablename__ = "evaluation_templates"

    id = Column(
        String, primary_key=True, index=True, default=lambda: str(uuid.uuid4())
    )
    name = Column(String(255), nullable=False, comment="模板名称")
    description = Column(Text, comment="模板描述")
    creator_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 模板内容
    questions = Column(JSON, nullable=False, comment="问题列表")
    default_scoring_criteria = Column(Text, comment="默认评分标准")
    recommended_models = Column(JSON, comment="推荐的评分模型")

    # 模板配置
    config = Column(JSON, comment="模板配置")
    tags = Column(JSON, comment="标签")

    # 统计信息
    usage_count = Column(Integer, default=0, comment="使用次数")

    # 状态
    is_public = Column(Boolean, default=False, comment="是否公开")
    is_active = Column(Boolean, default=True, comment="是否活跃")

    # 时间戳
    created_at = Column(
        DateTime(timezone=True), server_default=sa.text("now()")
    )
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text("now()"))

    # 关系
    creator = relationship("User")
