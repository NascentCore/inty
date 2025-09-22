// 智能体管理系统类型定义

// 从 SDK 导入 Agent 类型
import type { Agent as BaseAgent, AgentVisibility } from 'inty_sdk/src/resources/api/v1/ai/agents';

// 扩展 Agent 类型以包含 meta_data 字段
export interface Agent extends BaseAgent {
  meta_data?: AgentMetaData;
}

export type { AgentVisibility };

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
  main_prompt?: string;
  personality?: string;
  mode_prompt?: string;
  avatar?: string;
  background?: string;
  background_images?: string[];
  voice_id?: string;
  llm_config?: LLMConfig;
  meta_data?: AgentMetaData;
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
  voice_id?: string;
  llm_config?: LLMConfig | null;
  meta_data?: AgentMetaData;
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
}

// 评测配置
export interface EvaluationConfig {
  agents: Agent[];
  questions: string[];
  scoring_model: string;
  scoring_criteria: string;
  parallel_limit: number;
  timeout: number;
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
}

// 评测会话创建请求
export interface EvaluationSessionCreateRequest {
  name: string;
  description?: string;
  config: EvaluationConfig;
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
export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
}

// 分页响应
export interface PaginatedResponse<T = any> {
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
