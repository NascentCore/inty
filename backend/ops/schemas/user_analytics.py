"""用户数据分析相关 Schema"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UserAnalyticsDateRange(BaseModel):
    """日期范围请求（支持双日期范围：注册日期 + 活跃日期）"""

    # 用户注册日期范围
    register_start_date: Optional[datetime] = Field(None, description="注册开始日期")
    register_end_date: Optional[datetime] = Field(None, description="注册结束日期")
    register_last_days: Optional[int] = Field(
        None, ge=1, le=365, description="注册最近N天"
    )
    # 用户活跃日期范围
    activity_start_date: Optional[datetime] = Field(None, description="活跃开始日期")
    activity_end_date: Optional[datetime] = Field(None, description="活跃结束日期")
    activity_last_days: Optional[int] = Field(
        None, ge=1, le=365, description="活跃最近N天"
    )


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


class UserAgentConversationSessionItem(BaseModel):
    """用户-角色分组内的会话详情"""

    chat_id: str
    message_count: int
    voice_message_count: int
    messages: List[ChatMessageResponse]


class UserAgentConversationItem(BaseModel):
    """按 user_id + agent_id 分组的聊天详情"""

    user_id: str
    auth_type: str
    user_created_at: Optional[str]
    nickname: Optional[str]
    email: Optional[str]
    agent_id: str
    agent_name: str
    session_count: int
    message_count: int
    voice_message_count: int
    sessions: List[UserAgentConversationSessionItem]


class PaginatedUserAgentConversationsResponse(BaseModel):
    """按 user_id + agent_id 分组后的分页聊天详情"""

    items: List[UserAgentConversationItem]
    total: int
    page: int
    size: int
    has_more: bool


class UserAnalyticsStatsResponse(BaseModel):
    """用户数据分析统计概览（与原始脚本逻辑一致）"""

    # 统计类型
    total_new_users: int = Field(description="用户数")
    total_chat_initiators: int = Field(
        description="发起聊天的人数（排除仅浏览开场白的用户）"
    )
    total_user_messages: int = Field(description="总发送消息数（排除AI回复和开场白）")
    total_ai_messages: int = Field(
        default=0, description="AI 回复消息数（排除开场白）"
    )
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
    # 开口率指标
    new_user_open_rate: float = Field(
        description="开口率（total_chat_initiators / total_new_users，0-100）"
    )
    # 生图统计
    total_image_generation_requests: int = Field(description="总生图请求数", default=0)
    total_image_generation_success: int = Field(description="成功次数", default=0)
    total_image_generation_failures: int = Field(description="失败次数", default=0)
    image_generation_success_rate: float = Field(
        description="成功率（百分比，0-100）", default=0.0
    )
    # 生图细分统计
    total_image_new_generation: int = Field(description="新生成图片次数", default=0)
    total_image_fallback_used: int = Field(description="使用兜底图片次数", default=0)
    # 语音通话统计（Live Chat）
    total_live_chat_users: int = Field(description="发起语音通话人数", default=0)
    total_live_chat_sessions: int = Field(
        description="总语音通话 session 数", default=0
    )
    total_live_chat_duration: int = Field(description="总通话时长（秒）", default=0)
    avg_live_chat_sessions_per_user: float = Field(
        description="人均语音通话次数", default=0.0
    )
    avg_live_chat_duration_per_user: float = Field(
        description="人均通话时长（秒）", default=0.0
    )
    avg_live_chat_duration_per_session: float = Field(
        description="每 session 平均时长（秒）", default=0.0
    )


class UserDailyMessageItem(BaseModel):
    """每日消息统计项"""

    date: str = Field(description="日期 (YYYY-MM-DD)")
    message_count: int = Field(description="消息数")
    session_count: int = Field(description="会话数")


class UserDailyMessagesResponse(BaseModel):
    """用户每日消息统计响应"""

    user_id: str
    email: Optional[str]
    nickname: Optional[str]
    auth_type: str
    created_at: Optional[str]
    gender: Optional[str] = Field(None, description="性别：MALE/FEMALE/OTHER")
    age_group: Optional[str] = Field(None, description="年龄段")
    daily_messages: List[UserDailyMessageItem]


class UserTodayStatsResponse(BaseModel):
    """用户当日统计响应"""

    today_message_count: int = Field(description="今日消息数")
    today_session_count: int = Field(description="今日会话数")
    total_generated_images: int = Field(description="用户总的生图数", default=0)


class UserSessionItem(BaseModel):
    """用户会话项"""

    chat_id: str
    agent_name: str
    agent_avatar_url: Optional[str] = Field(None, description="角色形象图片 URL")
    created_at: Optional[str]
    updated_at: Optional[str]
    message_count: int


class UserSessionsResponse(BaseModel):
    """用户会话列表响应"""

    sessions: List[UserSessionItem]


class SessionMessageItem(BaseModel):
    """会话消息项"""

    id: int
    message_type: str
    content: Optional[str]
    created_at: Optional[str]
    audio_url: Optional[str]
    meta_data: Optional[Dict[str, Any]]


class SessionMessagesResponse(BaseModel):
    """会话消息列表响应"""

    messages: List[SessionMessageItem]
    total: int
    page: int
    size: int
    has_more: bool


class LLMLatencyItem(BaseModel):
    """LLM 延迟统计项"""

    hour: str = Field(description="小时时间戳 (YYYY-MM-DD HH:00)")
    avg_latency: float = Field(description="平均延迟 (秒)")
    count: int = Field(description="请求数量")


class LLMLatencyResponse(BaseModel):
    """LLM 延迟趋势响应"""

    data: List[LLMLatencyItem]


class ImageGenerationLatencyItem(BaseModel):
    """生图耗时统计项"""

    hour: str = Field(description="小时时间戳 (YYYY-MM-DD HH:00)")
    model: str = Field(description="生图模型名称")
    avg_latency_ms: float = Field(description="平均耗时 (毫秒)")
    count: int = Field(description="请求数量")


class ImageGenerationLatencyResponse(BaseModel):
    """生图耗时趋势响应"""

    data: List[ImageGenerationLatencyItem]


class ImageGenerationFailureAnalyticsResponse(BaseModel):
    """生图失败与兜底分析响应（只读 replica，与日报口径一致）"""

    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="summary, fallback_stats, failures_by_type, failures_by_reason, daily_trend, failures_by_agent",
    )


class LiveChatLatencyItem(BaseModel):
    """Live Chat 延迟统计项"""

    hour: str = Field(description="小时时间戳 (YYYY-MM-DD HH:00)")
    avg_connect_latency: Optional[float] = Field(
        default=None, description="平均连接延迟 (毫秒)"
    )
    avg_first_response_after_silence: Optional[float] = Field(
        default=None, description="平均静默后首响应延迟 (毫秒)"
    )
    avg_turn_latency: Optional[float] = Field(
        default=None, description="平均轮次延迟 (毫秒)"
    )
    count: int = Field(description="会话数量")


class LiveChatLatencyResponse(BaseModel):
    """Live Chat 延迟趋势响应"""

    data: List[LiveChatLatencyItem]


class LiveChatBasicStatsResponse(BaseModel):
    """Live Chat 基础统计响应"""

    total_users: int = Field(description="发起语音通话人数", default=0)
    total_sessions: int = Field(description="总语音通话 session 数", default=0)
    total_duration: int = Field(description="总通话时长（秒）", default=0)
    avg_sessions_per_user: float = Field(description="人均语音通话次数", default=0.0)
    avg_duration_per_user: float = Field(description="人均通话时长（秒）", default=0.0)
    avg_duration_per_session: float = Field(
        description="每 session 平均时长（秒）", default=0.0
    )


class UserGeneratedImageItem(BaseModel):
    """用户生成图片项"""

    url: str = Field(description="CDN URL")
    gcs_url: str = Field(description="GCS URL")
    generation_prompt: str = Field(description="生成提示词")
    reference_image_url: Optional[str] = Field(None, description="参考图片URL")
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")
    created_at: Optional[str] = Field(None, description="创建时间")
    agent_id: Optional[str] = Field(None, description="角色ID")
    agent_name: Optional[str] = Field(None, description="角色名称")


class UserGeneratedImagesResponse(BaseModel):
    """用户生成图片列表响应"""

    images: List[UserGeneratedImageItem]
    total: int = Field(description="总数量")


class UserAnalyticsReportGeneratedImageItem(BaseModel):
    """日报中的生图列表项"""

    id: int = Field(description="chat_history ID")
    session_id: str = Field(description="会话 session_id")
    image_url: str = Field(
        description="图片 URL（gs:// 已转换为 https://storage.googleapis.com/）"
    )
    meta_data: Dict[str, Any] = Field(default_factory=dict, description="消息元数据")
    created_at: Optional[str] = Field(None, description="创建时间")


class VoiceAudioItem(BaseModel):
    """单条语音录音项（播报或通话）"""

    audio_url: str = Field(description="GCS 或 CDN 音频 URL")
    message_id: int = Field(description="chat_history 消息 ID")
    created_at: Optional[str] = Field(None, description="创建时间 ISO 字符串")
    duration_seconds: Optional[float] = Field(None, description="音频时长（秒）")


class VoiceAudioGroupByUserAgent(BaseModel):
    """按用户-角色分组的语音录音列表"""

    user_id: str = Field(description="用户 ID")
    agent_id: str = Field(description="角色 ID")
    agent_name: str = Field(default="", description="角色名称")
    audios: List[VoiceAudioItem] = Field(
        default_factory=list, description="该用户-角色下的录音列表"
    )


class DailyVoiceAudiosResponse(BaseModel):
    """日报当日语音播报与语音通话录音（按用户-角色分组）"""

    voice_message_audios: List[VoiceAudioGroupByUserAgent] = Field(
        default_factory=list, description="语音播报（TTS）按用户-角色分组"
    )
    voice_call_audios: List[VoiceAudioGroupByUserAgent] = Field(
        default_factory=list, description="语音通话录音按用户-角色分组"
    )


class UserAnalyticsReportDailyTopAgentItem(BaseModel):
    """日报中按聊天轮数排序的角色项"""

    rank: int = Field(description="当日排名（1 开始）")
    agent_name: str = Field(description="角色名称")
    total_rounds: int = Field(description="总聊天轮数")
    user_count: int = Field(description="真实发起聊天人数", default=0)
    total_sessions: int = Field(description="浏览会话数", default=0)
    active_sessions: int = Field(description="有用户消息的会话数", default=0)


class UserAnalyticsReportCharts(BaseModel):
    """用户数据分析预计算报告图表数据"""

    new_users: List[Dict[str, Any]] = Field(
        default_factory=list, description="每日新用户"
    )
    conversation_rounds: List[Dict[str, Any]] = Field(
        default_factory=list, description="对话轮数（按Session）"
    )
    user_rounds_distribution: List[Dict[str, Any]] = Field(
        default_factory=list, description="对话轮数分布（按用户）"
    )
    users_hitting_limit: List[Dict[str, Any]] = Field(
        default_factory=list, description="达到聊天限制的用户"
    )
    popular_agents: List[Dict[str, Any]] = Field(
        default_factory=list, description="热门角色排行"
    )
    generated_images: List[UserAnalyticsReportGeneratedImageItem] = Field(
        default_factory=list, description="日报当日生图列表"
    )
    daily_top_agents_by_rounds: List[UserAnalyticsReportDailyTopAgentItem] = Field(
        default_factory=list, description="日报当日聊天轮数 Top 角色（默认 Top10）"
    )
    daily_most_discussed_agent: Optional[UserAnalyticsReportDailyTopAgentItem] = Field(
        None, description="日报当日聊天轮数最高角色"
    )


class UserAnalyticsReportItem(BaseModel):
    """用户数据分析预计算报告项"""

    id: str = Field(description="报告 ID")
    report_type: str = Field(description="daily | weekly")
    report_date: str = Field(
        description="日报：统计日期；周报：该周周一日期 (YYYY-MM-DD)"
    )
    stats: UserAnalyticsStatsResponse = Field(description="聚合统计数据")
    daily_top_agents_by_rounds: List[UserAnalyticsReportDailyTopAgentItem] = Field(
        default_factory=list,
        description="日报当日聊天轮数 Top 角色（用于轻量列表请求）",
    )
    daily_most_discussed_agent: Optional[UserAnalyticsReportDailyTopAgentItem] = Field(
        None,
        description="日报当日聊天轮数最高角色（用于轻量列表请求）",
    )
    charts: Optional[UserAnalyticsReportCharts] = Field(None, description="图表数据")
    created_at: Optional[str] = Field(None, description="创建时间")


class UserAnalyticsReportsResponse(BaseModel):
    """用户数据分析预计算报告列表响应"""

    reports: List[UserAnalyticsReportItem] = Field(
        default_factory=list, description="报告列表"
    )
