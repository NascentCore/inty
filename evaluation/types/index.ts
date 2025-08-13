/**
 * 评测系统类型定义
 * 基于后端API schemas重新设计，采用现代TypeScript最佳实践
 */

// =============================================================================
// 基础类型
// =============================================================================

export type EvaluationStatus =
  | "PENDING"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export type AgentGender = "MALE" | "FEMALE" | "OTHER";

export type AgentVisibility = "PUBLIC" | "PRIVATE";

// =============================================================================
// 智能体相关类型
// =============================================================================

export interface Agent {
  id: string;
  name: string;
  gender: AgentGender;
  avatar?: string;
  intro?: string;
  opening?: string;
  visibility: AgentVisibility;
  category?: string;
  creator_id?: string;
  created_at: string;
  updated_at?: string;
  // 评测相关字段
  main_prompt?: string;
  personality?: string;
  mode_prompt?: string;
  llm_config?: LLMConfig;
}

export interface LLMConfig {
  model: string;
  temperature: number;
  max_tokens: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
}

export interface AgentCreateRequest {
  name: string;
  gender: AgentGender;
  avatar?: string;
  intro: string;
  opening: string;
  visibility: AgentVisibility;
  main_prompt: string;
  personality: string;
  mode_prompt: string;
  modelType?: "default" | "custom";
  llm_config?: LLMConfig;
}

export interface AgentUpdateRequest extends Partial<AgentCreateRequest> {
  id: string;
}

// =============================================================================
// 评测会话相关类型
// =============================================================================

export interface EvaluationSession {
  id: string;
  name: string;
  creator_id: string;
  status: EvaluationStatus;
  questions: string[];
  selected_agents: string[];
  scoring_model: string;
  scoring_criteria?: string;
  use_new_user_identity: boolean;
  config?: Record<string, any>;
  total_tests: number;
  completed_tests: number;
  success_rate?: number;
  average_score?: number;
  created_at: string;
  updated_at?: string;
  started_at?: string;
  completed_at?: string;
}

export interface EvaluationSessionCreateRequest {
  name: string;
  questions: string[];
  selected_agents: string[];
  scoring_model: string;
  scoring_criteria?: string;
  use_new_user_identity?: boolean;
  config?: Record<string, any>;
}

export interface EvaluationResult {
  id: string;
  session_id: string;
  agent_id: string;
  agent_name?: string;
  question: string;
  question_index: number;
  agent_response?: string;
  response_time?: number;
  overall_score?: number;
  detailed_scores?: Record<string, number>;
  scoring_reason?: string;
  scoring_model_used?: string;
  is_success: boolean;
  error_message?: string;
  extra_data?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export interface EvaluationInteraction {
  id: string;
  session_id: string;
  result_id: string;
  chat_id?: string;
  user_input?: string;
  agent_response?: string;
  interaction_order?: number;
  user_identity?: Record<string, any>;
  response_metadata?: Record<string, any>;
  created_at: string;
}

export interface EvaluationSessionDetail extends EvaluationSession {
  results: EvaluationResult[];
  interactions: EvaluationInteraction[];
}

// =============================================================================
// 评测模板相关类型
// =============================================================================

export interface EvaluationTemplate {
  id: string;
  name: string;
  description?: string;
  creator_id: string;
  questions: string[];
  default_scoring_criteria?: string;
  recommended_models?: string[];
  config?: Record<string, any>;
  tags?: string[];
  usage_count: number;
  is_public: boolean;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface EvaluationTemplateCreateRequest {
  name: string;
  description?: string;
  questions: string[];
  default_scoring_criteria?: string;
  recommended_models?: string[];
  config?: Record<string, any>;
  tags?: string[];
  is_public?: boolean;
}

// =============================================================================
// 评分模型相关类型
// =============================================================================

export interface ScoringModel {
  id: string;
  name: string;
  description?: string;
  context_length?: number;
  provider?: string;
}

// =============================================================================
// 问题解析相关类型
// =============================================================================

export interface QuestionFileUpload {
  questions: string[];
  total_count: number;
  valid_count: number;
  duplicates_removed: number;
  warnings: string[];
}

export interface QuestionValidation {
  is_valid: boolean;
  issues: string[];
  warnings: string[];
  stats: {
    total: number;
    valid: number;
    duplicates: number;
    short_questions: number;
    long_questions: number;
  };
}

// =============================================================================
// WebSocket相关类型
// =============================================================================

export interface WebSocketMessage {
  type: string;
  session_id: string;
  data?: Record<string, any>;
  timestamp: string;
}

export type WebSocketMessageType =
  | "session_started"
  | "test_started"
  | "test_completed"
  | "session_completed"
  | "session_failed"
  | "session_cancelled"
  | "progress_update";

export interface WebSocketProgress {
  type: "progress_update";
  session_id: string;
  data: {
    current_test: number;
    total_tests: number;
    progress: number;
    current_agent?: string;
    current_question?: string;
  };
}

export interface WebSocketTestResult {
  type: "test_completed";
  session_id: string;
  data: {
    result: EvaluationResult;
    agent_name?: string;
  };
}

// =============================================================================
// UI组件相关类型
// =============================================================================

export interface FormOption<T = string> {
  label: string;
  value: T;
  disabled?: boolean;
}

export interface TableColumn<T = any> {
  key: string;
  title: string;
  dataIndex?: string;
  render?: (value: any, record: T, index: number) => React.ReactNode;
  width?: number | string;
  align?: "left" | "center" | "right";
  sorter?: boolean | ((a: T, b: T) => number);
  filters?: Array<{ text: string; value: any }>;
  onFilter?: (value: any, record: T) => boolean;
}

export interface PaginationConfig {
  current: number;
  pageSize: number;
  total: number;
  showSizeChanger?: boolean;
  showQuickJumper?: boolean;
  showTotal?: (total: number, range: [number, number]) => React.ReactNode;
}

// =============================================================================
// API响应类型
// =============================================================================

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  errors?: Record<string, string[]>;
}

export interface PaginatedResponse<T = any> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// =============================================================================
// 导出和对比相关类型
// =============================================================================

export interface ExportRequest {
  session_ids: string[];
  format: "csv" | "json" | "xlsx";
  include_interactions?: boolean;
  include_metadata?: boolean;
}

export interface ComparisonResult {
  agents: string[];
  questions: string[];
  results: Record<string, Record<string, any>>;
  summary: {
    best_agent?: string;
    average_score?: number;
    score_variance?: number;
  };
}

// =============================================================================
// 统计相关类型
// =============================================================================

export interface EvaluationStats {
  total_sessions: number;
  completed_sessions: number;
  running_sessions: number;
  failed_sessions: number;
  average_score?: number;
  success_rate?: number;
  total_tests: number;
  total_agents_tested: number;
}

// =============================================================================
// Hook相关类型
// =============================================================================

export interface UseEvaluationSessionOptions {
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export interface UseWebSocketOptions {
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

// =============================================================================
// 错误类型
// =============================================================================

export interface ApiError {
  message: string;
  code?: string;
  status?: number;
  details?: Record<string, any>;
}

export interface ValidationError {
  field: string;
  message: string;
  code?: string;
}
