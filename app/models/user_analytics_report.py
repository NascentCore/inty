# CREATED_BY_AGENT
"""
用户数据分析预计算报告模型

user_analytics_report: 存储日报/周报的预计算聚合统计，供独立页面快速展示。
"""

import uuid

from sqlalchemy import Column, Date, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.models.base import Base


class UserAnalyticsReport(Base):
    """用户数据分析预计算报告（日报/周报）"""

    __tablename__ = "user_analytics_report"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    report_type = Column(
        String(16),
        nullable=False,
        comment="daily | weekly",
    )
    report_date = Column(
        Date,
        nullable=False,
        comment="日报：统计日期；周报：该周周一日期",
    )
    stats = Column(
        JSONB,
        nullable=False,
        comment="UserAnalyticsStatsResponse 的完整 JSON",
    )
    charts = Column(
        JSONB,
        nullable=True,
        comment=(
            "图表数据：new_users, conversation_rounds, user_rounds_distribution, "
            "users_hitting_limit, popular_agents, generated_images, "
            "daily_top_agents_by_rounds, daily_most_discussed_agent"
        ),
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
