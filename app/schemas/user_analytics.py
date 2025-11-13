"""用户数据分析相关 Schema"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UserAnalyticsDateRange(BaseModel):
    """日期范围请求"""

    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    last_days: Optional[int] = Field(None, ge=1, le=365, description="最近N天")


class DailyNewUsersResponse(BaseModel):
    """每日新用户统计"""

    date: str
    auth_type: str
    count: int


class UserChatActivityItem(BaseModel):
    """用户聊天活动原始数据项"""

    user_id: str
    auth_type: str
    created_at: Optional[str]
    nickname: Optional[str]
    email: Optional[str]
    chat_id: Optional[str]
    agent_id: Optional[str]
    agent_name: Optional[str]


class UserChatActivityResponse(BaseModel):
    """用户聊天活动汇总"""

    user_id: str
    auth_type: str
    created_at: str
    nickname: Optional[str]
    email: Optional[str]
    session_count: int
    agent_names: List[str]
    total_rounds: int


class ConversationRoundsResponse(BaseModel):
    """对话轮数分布（按Session）"""

    chat_id: str
    message_count: int
    message_count_excluding_opening: int


class UserRoundsDistributionItem(BaseModel):
    """用户轮数分布项"""

    user_id: str
    total_rounds: int


class PopularAgentsResponse(BaseModel):
    """热门角色排行"""

    agent_name: str
    user_count: int
    total_rounds: int
    avg_rounds_per_user: float = Field(
        description="人均聊天轮数（total_rounds / user_count）"
    )
    pct_sessions_ge_5: float = Field(description=">=5轮会话百分比（0-100）")
    pct_sessions_ge_10: float = Field(description=">=10轮会话百分比（0-100）")
    total_sessions: int = Field(
        description="浏览数（总的session数，包含没有用户发送消息的session）"
    )
    active_sessions: int = Field(
        description="真实发起聊天的session数（有用户消息的session）"
    )
    open_rate: float = Field(
        description="开口率（active_sessions / total_sessions，0-100）"
    )


class UsersHittingLimitResponse(BaseModel):
    """达到聊天限制的用户"""

    date: str
    user_id: str
    auth_type: str
    nickname: Optional[str]
    email: Optional[str]
    chat_count_24h: int
    limit_value: int


class AgentAnalyticsResponse(BaseModel):
    """角色数据分析"""

    agent_id: str
    agent_name: str
    chat_user_count: int
    total_sessions: int
    total_rounds: int
    avg_rounds_per_user: float
    sessions_ge_5_rounds: int
    sessions_ge_10_rounds: int
    ge_5_rounds_ratio: float
    ge_10_rounds_ratio: float


class UserSessionsDetailResponse(BaseModel):
    """用户会话详情"""

    user_id: str
    auth_type: str
    user_created_at: Optional[str]
    nickname: Optional[str]
    email: Optional[str]
    chat_id: str
    agent_name: str
    message_count: int
    voice_message_count: int


class ChatMessageResponse(BaseModel):
    """聊天消息详情"""

    chat_id: str
    message_type: str
    content: Optional[str]
    created_at: Optional[str]
    audio_url: Optional[str]


class ConversationsDetailResponse(BaseModel):
    """对话详情（包含用户会话和消息）"""

    user_id: str
    auth_type: str
    user_created_at: Optional[str]
    nickname: Optional[str]
    email: Optional[str]
    sessions: List[Dict[str, Any]]


class UserAnalyticsStatsResponse(BaseModel):
    """用户数据分析统计概览（与原始脚本逻辑一致）"""

    # 统计类型
    total_new_users: int = Field(description="新增用户数")
    total_chat_initiators: int = Field(
        description="发起聊天的人数（排除仅浏览开场白的用户）"
    )
    total_user_messages: int = Field(description="总发送消息数（排除AI回复和开场白）")
    total_active_sessions: int = Field(
        description="包含用户消息的会话数（排除仅浏览开场白的会话）"
    )
    total_voice_requests: int = Field(description="总语音请求数（排除开场白语音）")
    # 用户维度（仅统计发送聊天的用户）
    avg_messages_per_user: float = Field(description="平均发送消息数")
    avg_sessions_per_user: float = Field(description="平均会话数")
    avg_voice_requests_per_user: float = Field(description="平均发起语音请求数")
    # 会话维度（包含用户消息的会话）
    avg_rounds_per_session: float = Field(description="每个会话平均轮数")
    # 新增指标
    new_user_open_rate: float = Field(
        description="新增用户开口率（total_chat_initiators / total_new_users，0-100）"
    )
