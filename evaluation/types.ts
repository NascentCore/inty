// 智能体管理系统类型定义

// 本地定义 Agent 基础类型，避免依赖 SDK 源码目录
export type AgentVisibility = "PUBLIC" | "PRIVATE";
export type AgentGender = "MALE" | "FEMALE" | "OTHER";

export interface AgentCreator {
  id?: string;
  email?: string;
  is_superuser?: boolean;
  [key: string]: unknown;
}

export interface AgentImageSize {
  width: number;
  height: number;
}

export interface AgentBaseExtensions {
  avatar_crop?: AvatarCropData;
  [key: string]: unknown;
}

export interface BaseAgent {
  id: string;
  name: string;
  visibility: AgentVisibility;
  gender: AgentGender;
  intro?: string;
  opening?: string;
  scenario?: string;
  main_prompt?: string;
  personality?: string;
  mode_prompt?: string;
  avatar?: string;
  background?: string;
  background_images?: string[];
  voice_id?: string;
  llm_config?: LLMConfig | null;
  extensions?: AgentBaseExtensions | null;
  tags?: string[];
  creator?: AgentCreator;
  created_at?: string;
  updated_at?: string;
  avatar_size?: AgentImageSize | null;
  background_size?: AgentImageSize | null;
  [key: string]: unknown;
}

/** 运营上传的专属角色照单条 */
export interface ExclusivePhotoItem {
  image_url: string;
  caption: string;
  credits_required: number;
}

/** 角色详情中的单条节日记忆（features.festival_memories） */
export interface FestivalMemoryItem {
  festival_date: string;
  festival_name: string;
  memory: string;
}

/** 角色可扩展功能数据，如节日记忆/心跳日记 */
export interface AgentFeatures {
  festival_memories?: FestivalMemoryItem[];
}

// 扩展 Agent 类型以包含 meta_data 和 background_animated 字段
export interface Agent extends BaseAgent {
  meta_data?: AgentMetaData;
  background_animated?: string; // webp 动图 URL
  description?: string; // 描述字段
  source?: AgentSource; // 角色来源
  features?: AgentFeatures;
  exclusive_photos?: ExclusivePhotoItem[]; // 运营专属角色照（评测管理用）
}

// 角色来源类型
export type AgentSource = "USER_CREATED" | "AUTO_GENERATED";

// 头像截取坐标信息类型
export interface AvatarCropData {
  x: number;
  y: number;
  width: number;
  height: number;
  imageWidth: number;
  imageHeight: number;
}

// Agent 元数据
export interface AgentMetaData {
  score?: number; // 1-5 的整数评分
  comment?: string; // 备注信息
}

// LLM 配置
export interface LLMConfig {
  model: string;
  temperature: number;
  max_tokens: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
}

// 创建智能体请求
export interface AgentCreateRequest {
  name: string;
  gender: "MALE" | "FEMALE" | "OTHER";
  intro?: string;
  opening?: string;
  visibility: "PUBLIC" | "PRIVATE";
  source?: AgentSource; // 角色来源
  main_prompt?: string;
  personality?: string;
  mode_prompt?: string;
  avatar?: string;
  background?: string;
  background_images?: string[];
  background_animated?: string; // webp 动图 URL
  voice_id?: string;
  llm_config?: LLMConfig;
  meta_data?: AgentMetaData;
  extensions?: { [key: string]: unknown }; // 扩展字段，如 avatar_crop
  tags?: string[];
}

// 更新智能体请求
export interface AgentUpdateRequest {
  name?: string;
  gender?: "MALE" | "FEMALE" | "OTHER";
  intro?: string;
  opening?: string;
  visibility?: "PUBLIC" | "PRIVATE";
  main_prompt?: string;
  personality?: string;
  mode_prompt?: string;
  avatar?: string;
  background?: string;
  background_images?: string[];
  replace_background_images?: boolean; // 是否替换 background_images 列表
  background_animated?: string; // webp 动图 URL
  voice_id?: string;
  llm_config?: LLMConfig | null;
  meta_data?: AgentMetaData;
  extensions?: { [key: string]: unknown } | null;
  tags?: string[];
  exclusive_photos?: ExclusivePhotoItem[];
}

// 生成背景视频请求
export interface GenerateBackgroundAnimatedRequest {
  prompt?: string; // 视频生成提示词（可选，如果为空则从背景图自动生成）
}

// 角色主题专区
export interface CharacterThemeAgent {
  agent_id: string;
  order_index: number;
  agent?: Agent;
}

export interface CharacterTheme {
  id: string;
  name: string;
  description?: string;
  background_image_url?: string;
  visibility: "PRIMARY" | "SECONDARY" | "HIDDEN";
  created_at: string;
  updated_at?: string;
  agents: CharacterThemeAgent[];
}

export interface CharacterThemeCreateRequest {
  name: string;
  description?: string;
  background_image_url?: string;
  visibility?: "PRIMARY" | "SECONDARY" | "HIDDEN";
}

export interface CharacterThemeUpdateRequest {
  name?: string;
  description?: string;
  background_image_url?: string;
  visibility?: "PRIMARY" | "SECONDARY" | "HIDDEN";
}

export interface AddAgentToThemeRequest {
  agent_id: string;
}

export interface ReorderAgentsRequest {
  agent_ids: string[];
}

// 聊天消息
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  remoteId?: string;
}

// 聊天会话
export interface ChatSession {
  id: string;
  agent_id: string;
  agent_name: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  messages: ChatMessage[];
}

// 评测会话
export interface EvaluationSession {
  id: string;
  name: string;
  description?: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  created_at: string;
  updated_at?: string;
  completed_at?: string;
  config: EvaluationConfig;
  progress?: EvaluationProgress;
  results?: EvaluationResult[];
  // 扩展字段
  selected_agents?: string[];
  questions?: string[];
}

// 评测配置
export interface EvaluationConfig {
  agents: Agent[];
  questions: string[];
  scoring_model: string;
  scoring_criteria: string;
  parallel_limit: number;
  timeout: number;
  use_new_user_identity?: boolean;
}

// 评测进度
export interface EvaluationProgress {
  total: number;
  completed: number;
  failed: number;
  current_agent?: string;
  current_question?: string;
  estimated_remaining?: number;
}

// WebSocket 消息
export interface WebSocketMessage {
  type: string;
  data?: unknown;
}

// Hook 选项
export interface UseEvaluationSessionOptions {
  autoRefresh?: boolean;
  refreshInterval?: number;
}

// 评测结果
export interface EvaluationResult {
  id: string;
  session_id: string;
  agent_id: string;
  agent_name: string;
  question: string;
  response: string;
  score: number;
  feedback: string;
  duration: number;
  created_at: string;
  // 扩展字段
  overall_score?: number;
  is_success?: boolean;
  question_index?: number;
  detailed_scores?: Record<string, unknown>;
  scoring_reason?: string;
  scoring_model_used?: string;
  response_time?: number;
  agent_response?: string;
  error_message?: string;
}

// 评测会话创建请求
export interface EvaluationSessionCreateRequest {
  name: string;
  description?: string;
  config: EvaluationConfig;
  questions?: string[];
  selected_agents?: string[];
  scoring_model?: string;
  scoring_criteria?: string;
  use_new_user_identity?: boolean;
}

// 评测模板
export interface EvaluationTemplate {
  id: string;
  name: string;
  description?: string;
  questions: string[];
  scoring_criteria: string;
  is_public: boolean;
  created_at: string;
  updated_at?: string;
}

// 评测模板创建请求
export interface EvaluationTemplateCreateRequest {
  name: string;
  description?: string;
  questions: string[];
  scoring_criteria: string;
  is_public: boolean;
}

// 评分模型
export interface ScoringModel {
  id: string;
  name: string;
  description: string;
  context_length: number;
  provider: string;
}

// OpenRouter模型
export interface OpenRouterModel {
  id: string;
  name: string;
  description?: string;
}

// 问题文件上传
export interface QuestionFileUpload {
  questions: string[];
  total_count: number;
  valid_count: number;
  duplicates_removed: number;
  warnings: string[];
}

// 表单验证错误
export interface ValidationError {
  field: string;
  message: string;
}

// 评测统计
export interface EvaluationStats {
  total_sessions: number;
  completed_sessions: number;
  running_sessions: number;
  failed_sessions: number;
  total_evaluations: number;
  average_score: number;
  top_agents: Array<{
    agent_id: string;
    agent_name: string;
    average_score: number;
    evaluation_count: number;
  }>;
}

// 导出请求
export interface ExportRequest {
  session_ids: string[];
  format: "json" | "csv" | "xlsx";
  include_details: boolean;
}

// 对比结果
export interface ComparisonResult {
  sessions: EvaluationSession[];
  comparison: {
    agents: Array<{
      agent_id: string;
      agent_name: string;
      average_score: number;
      total_evaluations: number;
      scores_by_session: Record<string, number>;
    }>;
    questions: Array<{
      question: string;
      average_score: number;
      scores_by_agent: Record<string, number>;
    }>;
    overall_stats: {
      best_agent: string;
      worst_agent: string;
      best_question: string;
      worst_question: string;
    };
  };
}

// API 响应通用格式
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

// 分页响应
export interface PaginatedResponse<T = unknown> {
  items: T[];
  total: number;
  page: number;
  size: number;
  has_more: boolean;
}

// 音色接口
export interface Voice {
  voice_id: string;
  name: string;
  category?: string;
  description?: string;
  voice_type?: string;
  provider?: "gemini" | "elevenlabs";
  gender?: string;
  source?: string;
  settings?: {
    stability?: number;
    similarity_boost?: number;
    style?: number;
    use_speaker_boost?: boolean;
  };
  samples?: Array<{
    sample_id: string;
    file_name: string;
    mime_type: string;
    size_bytes?: number;
    hash?: string;
  }>;
  labels?: Record<string, string>;
  preview_url?: string;
  available_for_tiers?: string[];
  high_quality_base_model_ids?: string[];
}

// 图片生成相关类型
export interface ChatImageGenerationRequest {
  message_id: number; // 必填：要生成图片的消息ID
  history_count?: number;
  request_id?: string;
}

export interface ChatImageGenerationResponse {
  image_url: string;
  image_metadata: {
    width: number;
    height: number;
    format: string;
  };
  prompt: string;
  message_id: number;
}

export interface ImageGenerationConfig {
  prompt_template: string;
  default_history_count: number;
}

// 用户数据分析相关类型
export interface DailyNewUsers {
  date: string;
  auth_type: "GUEST" | "GOOGLE";
  count: number;
}

export interface UserChatActivityItem {
  user_id: string;
  auth_type: string;
  created_at: string | null;
  nickname: string | null;
  email: string | null;
  chat_id: string | null;
  agent_id: string | null;
  agent_name: string | null;
}

export interface UserChatActivityResponse {
  user_id: string;
  auth_type: string;
  created_at: string;
  nickname: string | null;
  email: string | null;
  session_count: number;
  agent_names: string[];
  total_rounds: number;
}

export interface ConversationRoundsResponse {
  chat_id: string;
  message_count: number;
  message_count_excluding_opening: number;
}

export interface UserRoundsDistributionItem {
  user_id: string;
  total_rounds: number;
}

export interface PopularAgentsResponse {
  agent_name: string;
  user_count: number;
  total_rounds: number;
  avg_rounds_per_user: number;
  pct_sessions_ge_5: number;
  pct_sessions_ge_10: number;
  total_sessions: number;
  active_sessions: number;
  open_rate: number;
}

export interface UsersHittingLimitResponse {
  date: string;
  user_id: string;
  auth_type: string;
  nickname: string | null;
  email: string | null;
  chat_count_24h: number;
  limit_value: number;
}

export interface AgentAnalyticsResponse {
  agent_id: string;
  agent_name: string;
  chat_user_count: number;
  total_sessions: number;
  total_rounds: number;
  avg_rounds_per_user: number;
  sessions_ge_5_rounds: number;
  sessions_ge_10_rounds: number;
  ge_5_rounds_ratio: number;
  ge_10_rounds_ratio: number;
}

export interface UserSessionsDetailResponse {
  user_id: string;
  auth_type: string;
  user_created_at: string | null;
  nickname: string | null;
  email: string | null;
  chat_id: string;
  agent_name: string;
  message_count: number;
  voice_message_count: number;
}

export interface ChatMessageResponse {
  chat_id: string;
  message_type: string;
  content: string | null;
  created_at: string | null;
  audio_url: string | null;
}

export interface ConversationsDetailSession {
  chat_id: string;
  agent_name: string;
  message_count: number;
  voice_message_count: number;
  messages: ChatMessageResponse[];
}

export interface ConversationsDetailResponse {
  user_id: string;
  auth_type: string;
  user_created_at: string | null;
  nickname: string | null;
  email: string | null;
  sessions: ConversationsDetailSession[];
}

export interface UserAgentConversationSession {
  chat_id: string;
  message_count: number;
  voice_message_count: number;
  messages: ChatMessageResponse[];
}

export interface UserAgentConversationItem {
  user_id: string;
  auth_type: string;
  user_created_at: string | null;
  nickname: string | null;
  email: string | null;
  agent_id: string;
  agent_name: string;
  session_count: number;
  message_count: number;
  voice_message_count: number;
  sessions: UserAgentConversationSession[];
}

export interface PaginatedUserAgentConversationsResponse {
  items: UserAgentConversationItem[];
  total: number;
  page: number;
  size: number;
  has_more: boolean;
}

export interface UserAnalyticsReportGeneratedImageItem {
  id: number;
  session_id: string;
  image_url: string;
  meta_data: Record<string, unknown>;
  created_at: string | null;
}

export interface UserAnalyticsReportDailyTopAgentItem {
  rank: number;
  agent_name: string;
  total_rounds: number;
  user_count: number;
  total_sessions: number;
  active_sessions: number;
}

export interface UserAnalyticsReportCharts {
  new_users: Array<{ date: string; auth_type: string; count: number }>;
  conversation_rounds: Array<{
    chat_id: string;
    message_count: number;
    message_count_excluding_opening: number;
  }>;
  user_rounds_distribution: Array<{
    user_id: string;
    total_rounds: number;
  }>;
  users_hitting_limit: Array<{
    date: string;
    user_id: string;
    auth_type: string;
    nickname: string | null;
    email: string | null;
    chat_count_24h: number;
    limit_value: number;
  }>;
  popular_agents: PopularAgentsResponse[];
  generated_images: UserAnalyticsReportGeneratedImageItem[];
  daily_top_agents_by_rounds: UserAnalyticsReportDailyTopAgentItem[];
  daily_most_discussed_agent: UserAnalyticsReportDailyTopAgentItem | null;
}

export interface UserAnalyticsReportItem {
  id: string;
  report_type: "daily" | "weekly";
  report_date: string;
  stats: UserAnalyticsStatsResponse;
  daily_top_agents_by_rounds: UserAnalyticsReportDailyTopAgentItem[];
  daily_most_discussed_agent: UserAnalyticsReportDailyTopAgentItem | null;
  charts: UserAnalyticsReportCharts | null;
  created_at: string | null;
}

export interface UserAnalyticsReportsResponse {
  reports: UserAnalyticsReportItem[];
}

export interface VoiceAudioItem {
  audio_url: string;
  message_id: number;
  created_at: string | null;
  duration_seconds: number | null;
}

export interface VoiceAudioGroupByUserAgent {
  user_id: string;
  agent_id: string;
  agent_name: string;
  audios: VoiceAudioItem[];
}

export interface DailyVoiceAudiosResponse {
  voice_message_audios: VoiceAudioGroupByUserAgent[];
  voice_call_audios: VoiceAudioGroupByUserAgent[];
}

export interface UserAnalyticsStatsResponse {
  // 统计类型
  total_new_users: number;
  total_chat_initiators: number;
  total_user_messages: number;
  total_ai_messages?: number;
  total_active_sessions: number;
  total_voice_requests: number;
  // 用户维度（仅统计发送聊天的用户）
  avg_messages_per_user: number;
  avg_sessions_per_user: number;
  avg_voice_requests_per_user: number;
  // 会话维度（包含用户消息的会话）
  avg_rounds_per_session: number;
  // 新增指标
  new_user_open_rate: number;
  // 生图统计
  total_image_generation_requests: number;
  total_image_generation_success: number;
  total_image_generation_failures: number;
  image_generation_success_rate: number;
  // 生图细分统计
  total_image_new_generation: number;
  total_image_fallback_used: number;
  // 语音通话统计（Live Chat）
  total_live_chat_users: number;
  total_live_chat_sessions: number;
  total_live_chat_duration: number;
  avg_live_chat_sessions_per_user: number;
  avg_live_chat_duration_per_user: number;
  avg_live_chat_duration_per_session: number;
}

export interface UserDailyMessageItem {
  date: string;
  message_count: number;
  session_count: number;
}

export interface UserDailyMessagesResponse {
  user_id: string;
  email: string | null;
  nickname: string | null;
  auth_type: string;
  created_at: string | null;
  gender: string | null;
  age_group: string | null;
  daily_messages: UserDailyMessageItem[];
}

export interface UserTodayStatsResponse {
  today_message_count: number;
  today_session_count: number;
  total_generated_images: number;
}

export interface UserSessionItem {
  chat_id: string;
  agent_name: string;
  agent_avatar_url?: string | null;
  created_at: string | null;
  updated_at: string | null;
  message_count: number;
}

export interface UserSessionsResponse {
  sessions: UserSessionItem[];
}

export interface SessionGeneratedImageMeta {
  image_url: string;
  width?: number;
  height?: number;
  [key: string]: unknown;
}

export interface SessionMessageMetaData {
  generated_image?: SessionGeneratedImageMeta;
  /** LangSmith trace ID for AI messages; frontend assembles URL via getLangsmithTraceUrl(trace_id) */
  langsmith_trace_id?: string;
  [key: string]: unknown;
}

export interface SessionMessageItem {
  id: number;
  message_type: string;
  content: string | null;
  image_url?: string | null; // 独立图片消息的 URL
  created_at: string | null;
  audio_url: string | null;
  meta_data: SessionMessageMetaData | null;
}

export interface SessionMessagesResponse {
  messages: SessionMessageItem[];
  total: number;
  page: number;
  size: number;
  has_more: boolean;
}

// LLM 延迟统计
export interface LLMLatencyItem {
  hour: string;
  avg_latency: number;
  count: number;
}

export interface LLMLatencyResponse {
  data: LLMLatencyItem[];
}

// 生图耗时统计
export interface ImageGenerationLatencyItem {
  hour: string;
  model: string;
  avg_latency_ms: number;
  count: number;
}

export interface ImageGenerationLatencyResponse {
  data: ImageGenerationLatencyItem[];
}

// Live Chat 延迟统计
export interface LiveChatLatencyItem {
  hour: string;
  avg_connect_latency: number | null;
  avg_first_response_after_silence: number | null;
  avg_turn_latency: number | null;
  count: number;
}

export interface LiveChatLatencyResponse {
  data: LiveChatLatencyItem[];
}

// Live Chat 基础统计
export interface LiveChatBasicStatsResponse {
  total_users: number;
  total_sessions: number;
  total_duration: number;
  avg_sessions_per_user: number;
  avg_duration_per_user: number;
  avg_duration_per_session: number;
}

// 生成图片
export interface GeneratedImage {
  url: string;
  gcs_url: string;
  generation_prompt: string;
  reference_image_url: string | null;
  user_reference_image_url?: string | null;
  reference_image_urls?: string[] | null;
  width: number | null;
  height: number | null;
  created_at: string | null;
  user_id: string | null;
  user_nickname: string | null;
  user_email: string | null;
  user_photo: string | null;
  model?: string | null;
  generation_time_ms?: number | null;
  model_fallback_due_to_429?: boolean | null;
  langsmith_trace_id?: string | null;
  langsmith_trace_url?: string | null;
  session_id?: string | null;
  meta_data?: Record<string, unknown> | null;
}

export interface GeneratedImagesResponse {
  images: GeneratedImage[];
  total: number;
}

export interface ImageCountsResponse {
  counts: Record<string, number>;
}

// 用户生成图片
export interface UserGeneratedImageItem {
  url: string;
  gcs_url: string;
  generation_prompt: string;
  reference_image_url: string | null;
  width: number | null;
  height: number | null;
  created_at: string | null;
  agent_id: string | null;
  agent_name: string | null;
}

export interface UserGeneratedImagesResponse {
  images: UserGeneratedImageItem[];
  total: number;
}

// Report/Feedback 相关类型
export type ReportTargetType = "USER" | "AGENT";
export type ReportStatus = "PENDING" | "PROCESSING" | "RESOLVED" | "REJECTED";
export type ReportType = "REPORT" | "FEEDBACK";

export interface ReporterUserInfo {
  id: string;
  readable_id: string | null;
  nickname: string | null;
  email: string | null;
  phone: string | null;
  created_at: string | null;
}

export interface ReportItem {
  id: string;
  target_id: string;
  target_type: ReportTargetType;
  reporter_id: string;
  reporter_user_info: ReporterUserInfo | null;
  reason_codes: string[];
  image_urls: string[];
  description: string | null;
  github_issue: string | null;
  status: ReportStatus;
  report_type: ReportType | null;
  created_at: string;
}

export interface ReportsListResponse {
  items: ReportItem[];
  total: number;
}

export interface ReportConversationGroupItem {
  user_id: string;
  agent_id: string;
  agent_name: string | null;
  chat_count: number;
  total_rounds: number;
  latest_message_at: string | null;
}

export interface ReportConversationGroupsResponse {
  items: ReportConversationGroupItem[];
  total: number;
}

export interface ReportConversationMessageItem {
  id: number;
  chat_id: string;
  message_type: string;
  content: string | null;
  image_url: string | null;
  created_at: string | null;
  audio_url: string | null;
  meta_data: Record<string, unknown> | null;
}

export interface ReportConversationMessagesResponse {
  user_id: string;
  agent_id: string;
  page: number;
  size: number;
  total_rounds: number;
  has_more: boolean;
  messages: ReportConversationMessageItem[];
}

// 节日记忆配置与执行
export interface FestivalMemoryConfigItem {
  id: number;
  festival_name: string;
  festival_date: string;
  prompt: string;
  enabled: boolean;
  /** 节日与执行时间所属时区，IANA 名如 Asia/Shanghai */
  timezone: string;
  /** 执行日期（该时区下），须不早于节日日期 */
  run_at_date: string | null;
  /** 执行时刻（该时区下本地小时）0-23 */
  run_at_hour: number | null;
  /** 最近一次被定时任务执行的时间 */
  last_run_at: string | null;
  /** 窗口内最少用户消息轮数，null 表示默认 15 */
  min_rounds_in_window?: number | null;
  /** 模型配置 JSON，null 表示使用默认模型 */
  llm_config?: LLMConfig | null;
}

export interface FestivalMemoryConfigCreate {
  festival_name: string;
  festival_date: string;
  prompt: string;
  enabled?: boolean;
  /** 节日与执行时间所属时区，IANA 名如 Asia/Shanghai，默认 UTC */
  timezone?: string;
  run_at_date: string;
  run_at_hour: number; // 0-23
  /** 窗口内最少用户消息轮数，不传则默认 15 */
  min_rounds_in_window?: number | null;
  /** 模型配置，不传或 null 表示使用默认模型 */
  llm_config?: LLMConfig | null;
}

export interface FestivalMemoryConfigUpdate {
  festival_name?: string;
  festival_date?: string;
  prompt?: string;
  enabled?: boolean;
  timezone?: string;
  run_at_date?: string;
  run_at_hour?: number; // 0-23
  /** 窗口内最少用户消息轮数，不传则默认 15 */
  min_rounds_in_window?: number | null;
  /** 模型配置，不传表示不更新，传 null 表示改为默认模型 */
  llm_config?: LLMConfig | null;
}

export interface FestivalMemoryExtractionRunRequest {
  config_id?: number;
  festival_name?: string;
  festival_date?: string;
  prompt?: string;
  /** 节日日期所属时区（仅当未传 config_id 时用于窗口计算） */
  timezone?: string;
  /** 窗口内最少用户消息轮数（仅当未传 config_id 时生效），不传则默认 15 */
  min_rounds_in_window?: number | null;
}

export interface FestivalMemoryExtractionRunResponse {
  total_pairs: number;
  success_count: number;
  failed_count: number;
}
