/**
 * 此处代码是评测系统调用 Inty 后端 API
 */

import type {
  Agent,
  AgentCreateRequest,
  AgentUpdateRequest,
  EvaluationSession,
  EvaluationSessionCreateRequest,
  EvaluationResult,
  EvaluationTemplate,
  EvaluationTemplateCreateRequest,
  ScoringModel,
  QuestionFileUpload,
  EvaluationStats,
  ExportRequest,
  ComparisonResult,
  Voice,
  CharacterTheme,
  CharacterThemeAgent,
  CharacterThemeCreateRequest,
  CharacterThemeUpdateRequest,
  AddAgentToThemeRequest,
  ReorderAgentsRequest,
  WebSocketMessage,
} from "../types";
import { message } from "antd";

// =============================================================================
// 基础API配置
// =============================================================================

// Error logging API that show messages on the page and console
export const logError = (msg: string) => {
  console.error(msg);
  message.error(msg);
};

// 全局 API Key 管理
let globalApiKey: string | null = null;

export const setGlobalApiKey = (apiKey: string | null) => {
  globalApiKey = apiKey;
};

export const getGlobalApiKey = (): string | null => {
  return globalApiKey;
};

// 评测用：以指定用户身份请求（仅 superuser 有效），用于加载该用户与角色的对话历史
let assumeUserId: string | null = null;

export const setAssumeUserId = (userId: string | null) => {
  assumeUserId = userId;
};

export const getAssumeUserId = (): string | null => {
  return assumeUserId;
};

/** 构建聊天 WebSocket 生产端点 URL（与 App / POST completions 同源逻辑）；token 通过 query 传递。 */
export const getChatWebSocketUrl = (baseUrl?: string): string => {
  const base =
    baseUrl ?? (typeof window !== "undefined" ? window.location.origin : "");
  const scheme = base.startsWith("https") ? "wss" : "ws";
  const host = base.replace(/^https?:\/\//, "");
  const token = getGlobalApiKey() ?? "";
  const params = new URLSearchParams({ token });
  const assumeId = getAssumeUserId();
  if (assumeId?.trim()) {
    params.set("assume_user_id", assumeId.trim());
  }
  return `${scheme}://${host}/api/v1/chat/ws?${params.toString()}`;
};

type RequestOptions = NonNullable<Parameters<typeof fetch>[1]>;
type QueryParamValue = string | number | boolean | null | undefined;

/** 对话模式选项（与后端 GET /chats/modes 一致） */
export interface ChatModeOptionCompat {
  id: string;
  short_name: string;
  name: string;
  description: string;
}

class ApiClient {
  private baseURL: string;
  private apiPrefix: string;
  private headers: Record<string, string>;

  constructor(baseURL: string, apiPrefix: string = "/api/v1") {
    this.baseURL = baseURL;
    // 如果baseURL已经包含api/v1，则不使用apiPrefix
    this.apiPrefix = baseURL.includes("/api/v1") ? "" : apiPrefix;
    // This is the default headers for all requests.
    // Some API endpoints needs different content header, like upload avatar,
    // needs multipart/form-data.
    this.headers = {
      "Content-Type": "application/json",
    };
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {},
  ): Promise<T> {
    // 自动添加API前缀，如果endpoint已经包含/api/则不添加
    const fullEndpoint = endpoint.startsWith("/api/")
      ? endpoint
      : `${this.apiPrefix}${endpoint}`;

    const url = `${this.baseURL}${fullEndpoint}`;

    // 使用动态 API Key，如果没有则抛出错误（在构建 config 之前检查）
    const currentApiKey = getGlobalApiKey();
    if (!currentApiKey || currentApiKey.trim() === "") {
      throw new Error("API Key 未设置，请先设置 API Key");
    }

    // 构建基础 headers，先合并默认 headers 和传入的 headers
    const requestHeaders = new Headers(this.headers);
    if (options.headers) {
      const customHeaders = new Headers(options.headers);
      customHeaders.forEach((value, key) => {
        requestHeaders.set(key, value);
      });
    }

    // 如果是上传请求（FormData），不要覆盖Content-Type
    if (options.body instanceof FormData) {
      requestHeaders.delete("Content-Type");
    }

    // 确保 Authorization header 总是最后设置，不会被覆盖
    requestHeaders.set("Authorization", `Bearer ${currentApiKey}`);

    const assumeId = getAssumeUserId();
    if (assumeId && assumeId.trim()) {
      requestHeaders.set("X-Assume-User-Id", assumeId.trim());
    }

    // 构建最终的 config 对象
    const config: RequestOptions = {
      ...options,
      headers: requestHeaders,
    };

    // 验证 Authorization header 是否已正确设置
    const authHeaderValue = requestHeaders.get("Authorization");
    const hasAuthHeader =
      typeof authHeaderValue === "string" && authHeaderValue.trim().length > 0;

    if (!hasAuthHeader) {
      throw new Error("Authorization header 设置失败");
    }

    try {
      // 确保 headers 是一个普通对象（不是 Headers 对象）
      // fetch API 可以接受 Headers 对象或普通对象，但为了确保兼容性，我们使用普通对象
      const finalHeaders: Record<string, string> = {};
      requestHeaders.forEach((value, key) => {
        finalHeaders[key] = value;
      });

      const finalConfig = {
        ...config,
        headers: finalHeaders,
      };

      const response = await fetch(url, finalConfig);

      class ApiError extends Error {
        public status: number;
        public statusText: string;
        public errorData: unknown;

        constructor(
          message: string,
          status: number,
          statusText: string,
          errorData: unknown,
        ) {
          super(message);
          this.name = "ApiError";
          this.status = status;
          this.statusText = statusText;
          this.errorData = errorData;
          // Set the prototype explicitly.
          Object.setPrototypeOf(this, ApiError.prototype);
        }
      }

      if (!response.ok) {
        const errorData: unknown = await response.json().catch(() => ({}));
        const parsedErrorMessage =
          typeof errorData === "object" &&
          errorData !== null &&
          "detail" in errorData &&
          typeof (errorData as { detail?: unknown }).detail === "string"
            ? (errorData as { detail: string }).detail
            : typeof errorData === "object" &&
                errorData !== null &&
                "message" in errorData &&
                typeof (errorData as { message?: unknown }).message === "string"
              ? (errorData as { message: string }).message
              : `HTTP ${response.status}: ${response.statusText}`;
        throw new ApiError(
          parsedErrorMessage,
          response.status,
          response.statusText,
          errorData,
        );
      }

      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        const result: unknown = await response.json();

        // Check if it's APIResponse format
        if (result && typeof result === "object" && "code" in result) {
          const apiResult = result as {
            code?: number;
            message?: string;
            data?: T;
          };

          if (apiResult.code === 200) {
            return apiResult.data as T;
          } else {
            throw new ApiError(
              apiResult.message || "API Error",
              response.status,
              response.statusText,
              result,
            );
          }
        } else {
          return result as T;
        }
      } else {
        return response as unknown as T;
      }
    } catch (error) {
      logError(`API请求失败: ${endpoint}, 错误信息: ${error}`);
      throw error;
    }
  }

  // GET请求
  async get<T>(
    endpoint: string,
    params?: Record<string, QueryParamValue> | object,
    options?: RequestOptions,
  ): Promise<T> {
    let finalEndpoint = endpoint;

    if (params && !("signal" in (params as object))) {
      const searchParams = new URLSearchParams();
      Object.entries(params as Record<string, QueryParamValue>).forEach(
        ([key, value]) => {
          if (value !== undefined && value !== null) {
            searchParams.append(key, String(value));
          }
        },
      );
      const queryString = searchParams.toString();
      if (queryString) {
        finalEndpoint += `?${queryString}`;
      }
    }

    return this.request<T>(finalEndpoint, { method: "GET", ...options });
  }

  // POST请求
  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // PUT请求
  async put<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // DELETE请求
  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, {
      method: "DELETE",
    });
  }

  // 文件上传
  async upload<T>(
    endpoint: string,
    file: File,
    additionalData?: Record<string, string | number | boolean>,
  ): Promise<T> {
    const formData = new FormData();
    formData.append("file", file);

    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, String(value));
      });
    }

    return this.request<T>(endpoint, {
      method: "POST",
      body: formData,
      headers: {}, // 让浏览器自动设置Content-Type
    });
  }
}

// 创建API客户端实例
const apiClient = new ApiClient(window.location.origin);

// 保留旧入口函数名，兼容现有调用链，内部仅维护全局 API Key
export const updateIntyClient = (apiKey: string | null) => {
  setGlobalApiKey(apiKey);
};

// =============================================================================
// 评测会话API
// =============================================================================

export const evaluationSessionApi = {
  // 创建评测会话
  create: (data: EvaluationSessionCreateRequest): Promise<EvaluationSession> =>
    apiClient.post("/evaluation/sessions", data),

  // 获取评测会话列表
  list: (params?: {
    skip?: number;
    limit?: number;
    status?: string;
  }): Promise<EvaluationSession[]> =>
    apiClient.get("/evaluation/sessions", params),

  // 获取评测会话详情
  get: (sessionId: string): Promise<EvaluationSession> =>
    apiClient.get(`/evaluation/sessions/${sessionId}`),

  // 启动评测会话
  start: (sessionId: string): Promise<{ success: boolean; message: string }> =>
    apiClient.post(`/evaluation/sessions/${sessionId}/start`),

  // 取消评测会话
  cancel: (sessionId: string): Promise<{ success: boolean; message: string }> =>
    apiClient.post(`/evaluation/sessions/${sessionId}/cancel`),

  // 获取评测结果
  getResults: (sessionId: string): Promise<EvaluationResult[]> =>
    apiClient.get(`/evaluation/sessions/${sessionId}/results`),

  // 删除评测会话
  delete: (sessionId: string): Promise<{ success: boolean; message: string }> =>
    apiClient.delete(`/evaluation/sessions/${sessionId}`),

  // 批量创建评测会话
  createBatch: (
    sessions: EvaluationSessionCreateRequest[],
  ): Promise<EvaluationSession[]> =>
    apiClient.post("/evaluation/sessions/batch", { sessions }),

  // 对比评测会话
  compare: (sessionIds: string[]): Promise<ComparisonResult> =>
    apiClient.post("/evaluation/sessions/compare", sessionIds),
};

// =============================================================================
// 智能体管理API
// =============================================================================

interface UploadAvatarResponse {
  url?: string;
  data?: {
    url?: string;
    avatar_url?: string;
  };
  [key: string]: unknown;
}

export const agentApi = {
  // 获取智能体列表 - API前缀由ApiClient自动处理
  list: (params?: {
    type?: "public" | "private";
    skip?: number;
    limit?: number;
  }): Promise<Agent[]> => apiClient.get("/ai/agents/me", params),

  // 管理员获取全量智能体列表（包含非管理员创建的角色）
  listAll: (params?: { skip?: number; limit?: number }): Promise<Agent[]> =>
    apiClient.get("/ai/agents/admin/list", params),

  // 获取推荐智能体 - 使用现有API
  getRecommended: (): Promise<Agent[]> => apiClient.get("/ai/agents/recommend"),

  // 搜索智能体 - 使用现有API
  search: (query: string): Promise<Agent[]> =>
    apiClient.get("/ai/agents/search", { q: query }),

  // 获取智能体详情 - 使用现有API
  get: (agentId: string): Promise<Agent> =>
    apiClient.get(`/ai/agents/${agentId}`),

  // 创建智能体 - 使用现有API
  create: (data: AgentCreateRequest): Promise<Agent> =>
    apiClient.post("/ai/agents", data),

  // 更新智能体 - 使用现有API
  update: (
    agentId: string,
    data: Partial<AgentUpdateRequest> & {
      replace_background_images?: boolean;
    },
  ): Promise<Agent> => apiClient.put(`/ai/agents/${agentId}`, data),

  // 删除智能体 - 使用现有API
  delete: (agentId: string): Promise<{ message: string }> =>
    apiClient.delete(`/ai/agents/${agentId}`),

  // 部署智能体到生产环境 - 如果存在的话
  deploy: (
    agentId: string,
    adminPassword: string,
  ): Promise<{
    success: boolean;
    message: string;
    agent_id: string;
    deploy_time: string;
  }> =>
    apiClient.post(`/ai/agents/${agentId}/deploy`, {
      admin_password: adminPassword,
    }),

  // 上传头像
  uploadAvatar: (
    file: File,
    croppingAvatar: boolean = true,
  ): Promise<UploadAvatarResponse> =>
    apiClient.upload<UploadAvatarResponse>("/images", file, {
      cropping_avatar: croppingAvatar,
    }),

  // 检查背景图宽高比
  checkBackgroundAspectRatio: (
    agentId: string,
  ): Promise<{
    is_9_16: boolean;
    width: number;
    height: number;
    aspect_ratio: number;
  }> =>
    apiClient.get(
      `/evaluation/agents/${agentId}/check-background-aspect-ratio`,
    ),

  // 上传裁剪后的背景图
  uploadCroppedBackground: (agentId: string, file: File): Promise<Agent> =>
    apiClient.upload(
      `/evaluation/agents/${agentId}/upload-cropped-background`,
      file,
    ),

  // 生成背景视频
  generateBackgroundAnimated: (
    agentId: string,
    prompt?: string,
  ): Promise<Agent> =>
    apiClient.post(`/ai/agents/${agentId}/generate-background-animated`, {
      prompt: prompt || undefined, // 如果为空字符串，发送 undefined
    }),

  // 获取可用的 prompt 列表
  getAvailablePrompts: (params?: {
    include_content?: boolean;
  }): Promise<{
    main_prompts: Array<{
      id: string;
      name: string;
      description: string;
      content?: string;
    }>;
    mode_prompts: Array<{
      id: string;
      name: string;
      description: string;
      content?: string;
    }>;
    force_default_prompts: boolean;
    default_main_prompt_id: string;
    default_mode_prompt_id: string;
  }> => apiClient.get("/ai/agents/prompts/available", params),
};

// =============================================================================
// 评测模板API
// =============================================================================

export const templateApi = {
  // 获取模板列表
  list: (params?: {
    include_public?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<EvaluationTemplate[]> =>
    apiClient.get("/evaluation/templates", params),

  // 创建模板
  create: (
    data: EvaluationTemplateCreateRequest,
  ): Promise<EvaluationTemplate> =>
    apiClient.post("/evaluation/templates", data),

  // 获取模板详情
  get: (templateId: string): Promise<EvaluationTemplate> =>
    apiClient.get(`/evaluation/templates/${templateId}`),

  // 更新模板
  update: (
    templateId: string,
    data: Partial<EvaluationTemplateCreateRequest>,
  ): Promise<EvaluationTemplate> =>
    apiClient.put(`/evaluation/templates/${templateId}`, data),

  // 删除模板
  delete: (templateId: string): Promise<{ message: string }> =>
    apiClient.delete(`/evaluation/templates/${templateId}`),
};

// =============================================================================
// 问题解析API
// =============================================================================

export const questionApi = {
  // 解析问题文件
  parseFile: (file: File): Promise<QuestionFileUpload> =>
    apiClient.upload("/evaluation/questions/parse", file),

  // 验证问题列表
  validate: (
    questions: string[],
  ): Promise<{
    is_valid: boolean;
    issues: string[];
    warnings: string[];
    stats: Record<string, number>;
  }> => apiClient.post("/evaluation/questions/validate", { questions }),
};

// =============================================================================
// 评分模型API
// =============================================================================

export const scoringApi = {
  // 获取可用模型 - 添加超时和错误处理
  getModels: async (): Promise<ScoringModel[]> => {
    try {
      // 设置较短的超时时间
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5秒超时

      const models = await apiClient.get("/evaluation/models", undefined, {
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      return models as ScoringModel[];
    } catch (error) {
      console.warn("获取评分模型失败，使用默认模型列表:", error);

      // 返回默认模型列表
      return [
        {
          id: "meta-llama/llama-3.1-405b-instruct",
          name: "Llama 3.1 405B Instruct",
          description: "Meta最新的大型语言模型，适合复杂的推理和评估任务",
          context_length: 32768,
          provider: "Meta",
        },
        {
          id: "anthropic/claude-3.5-sonnet",
          name: "Claude 3.5 Sonnet",
          description: "Anthropic的Claude模型，擅长分析和评估",
          context_length: 200000,
          provider: "Anthropic",
        },
        {
          id: "openai/gpt-4o",
          name: "GPT-4o",
          description: "OpenAI的多模态模型，具有强大的理解能力",
          context_length: 128000,
          provider: "OpenAI",
        },
        {
          id: "google/gemini-pro-1.5",
          name: "Gemini Pro 1.5",
          description: "Google的Gemini模型，支持长上下文",
          context_length: 2000000,
          provider: "Google",
        },
        {
          id: "openai/gpt-4o-mini",
          name: "GPT-4o Mini",
          description: "OpenAI的轻量级模型，快速且经济",
          context_length: 128000,
          provider: "OpenAI",
        },
        {
          id: "anthropic/claude-3.5-haiku",
          name: "Claude 3.5 Haiku",
          description: "Anthropic的快速模型，适合简单评估任务",
          context_length: 200000,
          provider: "Anthropic",
        },
      ];
    }
  },

  // 验证评分标准
  validateCriteria: (
    criteria: string,
  ): Promise<{
    is_valid: boolean;
    issues: string[];
    suggestions: string[];
  }> => apiClient.post("/evaluation/scoring-criteria/validate", { criteria }),

  // 获取OpenRouter完整模型列表
  getOpenRouterModels: (): Promise<
    {
      id: string;
      name: string;
      description?: string;
    }[]
  > => apiClient.get("/ai/agents/models/openrouter"),
};

// =============================================================================
// 音色管理API
// =============================================================================

export const voiceApi = {
  // 获取音色列表
  listVoices: (params?: {
    search?: string;
    page_size?: number;
    voice_type?: string;
    category?: string;
    provider?: string;
  }): Promise<Voice[]> => apiClient.get("/text-to-speech/list-voices", params),
};

// =============================================================================
// 统计和导出API
// =============================================================================

export const statsApi = {
  // 获取统计信息
  get: (days?: number): Promise<EvaluationStats> =>
    apiClient.get("/evaluation/stats", { days }),

  // 导出评测结果
  export: (
    data: ExportRequest,
  ): Promise<{
    download_url: string;
    format: string;
    session_count: number;
  }> => apiClient.post("/evaluation/results/export", data),
};

// =============================================================================
// 订阅信息 API
// =============================================================================

export const subscriptionApi = {
  getStatus: (): Promise<Record<string, unknown>> =>
    apiClient.get("/subscription/status"),
};

// =============================================================================
// 用户数据分析API
// =============================================================================

// 双日期范围参数类型
interface AnalyticsDateParams {
  // 注册日期范围
  register_start_date?: string;
  register_end_date?: string;
  register_last_days?: number;
  // 活跃日期范围
  activity_start_date?: string;
  activity_end_date?: string;
  activity_last_days?: number;
}

type UserLookupParams = {
  email?: string;
  user_id?: string;
};

export const userAnalyticsApi = {
  // 获取统计数据
  getStats: (
    params?: AnalyticsDateParams,
  ): Promise<import("../types").UserAnalyticsStatsResponse> =>
    apiClient.get("/evaluation/user-analytics/stats", params),

  // 获取预计算报告列表（日报/周报）
  getReports: (params?: {
    report_type?: "daily" | "weekly";
    limit?: number;
    include_charts?: boolean;
  }): Promise<import("../types").UserAnalyticsReportsResponse> =>
    apiClient.get("/evaluation/user-analytics/reports", params),

  // 获取指定日期的语音播报与语音通话录音（按用户-角色分组）
  getDailyVoiceAudios: (
    report_date: string,
  ): Promise<import("../types").DailyVoiceAudiosResponse> =>
    apiClient.get("/evaluation/user-analytics/daily-voice-audios", {
      report_date,
    }),

  // 获取用户注册统计
  getNewUsers: (
    params?: AnalyticsDateParams,
  ): Promise<import("../types").DailyNewUsers[]> =>
    apiClient.get("/evaluation/user-analytics/new-users", params),

  // 获取用户聊天活动原始数据
  getUserActivity: (
    params?: AnalyticsDateParams,
  ): Promise<import("../types").UserChatActivityItem[]> =>
    apiClient.get("/evaluation/user-analytics/user-activity", params),

  // 获取对话轮数分布（按Session）
  getConversationRounds: (
    params?: AnalyticsDateParams,
  ): Promise<import("../types").ConversationRoundsResponse[]> =>
    apiClient.get("/evaluation/user-analytics/conversation-rounds", params),

  // 获取对话轮数分布（按用户）
  getUserRoundsDistribution: (
    params?: AnalyticsDateParams,
  ): Promise<import("../types").UserRoundsDistributionItem[]> =>
    apiClient.get(
      "/evaluation/user-analytics/user-rounds-distribution",
      params,
    ),

  // 获取热门角色排行
  getPopularAgents: (
    params?: AnalyticsDateParams,
  ): Promise<import("../types").PopularAgentsResponse[]> =>
    apiClient.get("/evaluation/user-analytics/popular-agents", params),

  // 获取达到聊天限制的用户（使用活跃日期范围）
  getUsersHittingLimit: (
    params?: AnalyticsDateParams,
  ): Promise<import("../types").UsersHittingLimitResponse[]> =>
    apiClient.get("/evaluation/user-analytics/users-hitting-limit", params),

  // 获取角色数据分析
  getAgentAnalytics: (
    params?: AnalyticsDateParams,
  ): Promise<import("../types").AgentAnalyticsResponse[]> =>
    apiClient.get("/evaluation/user-analytics/agent-analytics", params),

  // 获取用户会话详情
  getUserSessionsDetail: (
    params?: AnalyticsDateParams,
  ): Promise<import("../types").UserSessionsDetailResponse[]> =>
    apiClient.get("/evaluation/user-analytics/user-sessions-detail", params),

  // 获取对话详情（包含消息内容）
  getConversationsDetail: (
    params?: AnalyticsDateParams,
  ): Promise<import("../types").ConversationsDetailResponse[]> =>
    apiClient.get("/evaluation/user-analytics/conversations-detail", params),

  // 获取按 user_id + agent_id 分组的分页对话详情
  getUserAgentConversationsDetailPaginated: (
    params?: AnalyticsDateParams & { page?: number; size?: number },
  ): Promise<import("../types").PaginatedUserAgentConversationsResponse> =>
    apiClient.get(
      "/evaluation/user-analytics/conversations-detail/user-agent-paginated",
      params,
    ),

  // 获取用户每日消息统计
  getUserDailyMessages: (
    params: UserLookupParams & {
      start_date?: string;
      end_date?: string;
    },
  ): Promise<import("../types").UserDailyMessagesResponse> =>
    apiClient.get("/evaluation/user-analytics/user-daily-messages", params),

  // 获取用户当日统计
  getUserTodayStats: (
    params: UserLookupParams,
  ): Promise<import("../types").UserTodayStatsResponse> =>
    apiClient.get("/evaluation/user-analytics/user-today-stats", params),

  // 获取用户的所有会话列表
  getUserSessions: (
    params: UserLookupParams,
  ): Promise<import("../types").UserSessionsResponse> =>
    apiClient.get("/evaluation/user-analytics/user-sessions", params),

  // 获取指定会话的对话历史
  getSessionMessages: (params: {
    chat_id: string;
    page?: number;
    size?: number;
  }): Promise<import("../types").SessionMessagesResponse> =>
    apiClient.get("/evaluation/user-analytics/session-messages", params),

  // 获取用户生成图片列表
  getUserGeneratedImages: (
    params: UserLookupParams & {
      skip?: number;
      limit?: number;
    },
  ): Promise<import("../types").UserGeneratedImagesResponse> =>
    apiClient.get("/evaluation/user-analytics/user-generated-images", params),

  // 获取 LLM 调用延迟趋势
  getLLMLatency: (
    params?: AnalyticsDateParams,
  ): Promise<import("../types").LLMLatencyResponse> =>
    apiClient.get("/evaluation/user-analytics/llm-latency", params),

  // 获取生图耗时趋势
  getImageGenerationLatency: (
    params?: AnalyticsDateParams,
  ): Promise<import("../types").ImageGenerationLatencyResponse> =>
    apiClient.get(
      "/evaluation/user-analytics/image-generation-latency",
      params,
    ),

  // 获取 Live Chat 延迟趋势
  getLiveChatLatency: (
    params?: AnalyticsDateParams,
  ): Promise<import("../types").LiveChatLatencyResponse> =>
    apiClient.get("/evaluation/user-analytics/live-chat-latency", params),

  // 获取 Live Chat 基础统计
  getLiveChatStats: (
    params?: AnalyticsDateParams,
  ): Promise<import("../types").LiveChatBasicStatsResponse> =>
    apiClient.get("/evaluation/user-analytics/live-chat-stats", params),
};

// =============================================================================
// WebSocket连接管理
// =============================================================================

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 3000;
  private listeners: Map<string, Set<(data: WebSocketMessage) => void>> =
    new Map();

  constructor(sessionId: string) {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    this.url = `${protocol}//${host}/api/v1/evaluation/sessions/${sessionId}/monitor`;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.log("WebSocket连接已建立");
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const parsedMessage = JSON.parse(event.data) as WebSocketMessage;
            this.handleMessage(parsedMessage);
          } catch (error) {
            console.error("WebSocket消息解析失败:", error);
          }
        };

        this.ws.onclose = (event) => {
          console.log("WebSocket连接已关闭:", event.code, event.reason);
          this.handleReconnect();
        };

        this.ws.onerror = (error) => {
          console.error("WebSocket连接错误:", error);
          reject(error);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  private handleMessage(message: WebSocketMessage) {
    const { type } = message;
    const listeners = this.listeners.get(type);

    if (listeners) {
      listeners.forEach((callback) => {
        try {
          callback(message);
        } catch (error) {
          console.error("WebSocket消息处理错误:", error);
        }
      });
    }

    // 广播给所有监听器
    const allListeners = this.listeners.get("*");
    if (allListeners) {
      allListeners.forEach((callback) => {
        try {
          callback(message);
        } catch (error) {
          console.error("WebSocket广播消息处理错误:", error);
        }
      });
    }
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(
        `尝试重连WebSocket (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`,
      );

      setTimeout(() => {
        this.connect().catch((error) => {
          console.error("WebSocket重连失败:", error);
        });
      }, this.reconnectInterval);
    } else {
      console.error("WebSocket重连次数已达上限");
    }
  }

  on(eventType: string, callback: (data: WebSocketMessage) => void) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)!.add(callback);
  }

  off(eventType: string, callback: (data: WebSocketMessage) => void) {
    const listeners = this.listeners.get(eventType);
    if (listeners) {
      listeners.delete(callback);
    }
    // callback parameter is required for type signature but may not be used
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.listeners.clear();
  }

  getReadyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }
}

// =============================================================================
// 聊天API - 调用现有的聊天系统
// =============================================================================

type ChatTextContentPart = {
  type: "text";
  text: string;
};

type ChatImageUrlContentPart = {
  type: "image_url";
  image_url: {
    url: string;
  };
};

type ChatMessageContent =
  | string
  | Array<ChatTextContentPart | ChatImageUrlContentPart>;

export const chatApi = {
  // 获取用户聊天列表
  getChats: (): Promise<
    Array<{
      id: string;
      agent_id: string;
      agent_name: string;
      is_active: boolean;
      created_at: string;
      updated_at: string;
    }>
  > => apiClient.get("/chats/"),

  // 创建新聊天会话
  createChat: (data: {
    agent_id: string;
  }): Promise<{
    id: string;
    agent_id: string;
    user_id: string;
    is_active: boolean;
    created_at: string;
  }> => apiClient.post("/chats/", data),

  // 使用现有的OpenAI兼容API发送消息 - 这是核心聊天接口
  sendMessage: (
    agentId: string,
    messages: Array<{
      role: "user" | "assistant";
      content: ChatMessageContent;
    }>,
    stream: boolean = false,
    options?: { localId?: string },
  ): Promise<{
    id: string;
    object: string;
    created: number;
    model: string;
    user_message_id?: number;
    local_id?: string;
    choices: Array<{
      index: number;
      message: {
        role: "assistant";
        content: string;
      };
      finish_reason: string;
    }>;
    usage: {
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
    };
  }> => {
    const body: Record<string, unknown> = {
      messages,
      stream,
      model: "chatbot",
      language: "zh",
    };
    if (options?.localId) {
      body.localId = options.localId;
    }
    return apiClient.post(`/chat/completions/${agentId}`, body);
  },

  // 获取Agent聊天详情和消息历史
  getChatDetail: (
    agentId: string,
    params?: {
      page?: number;
      size?: number;
    },
  ): Promise<{
    chat_info: {
      id: string;
      agent_id: string;
      user_id: string;
      created_at: string;
      updated_at: string;
    };
    messages: Array<{
      id?: number;
      role: "user" | "assistant" | null;
      sender_type: "USER" | "AI" | null;
      content: string;
      created_at: string;
      timestamp: string;
      type?: "text" | "image" | "festival_memory_prompt";
      festival_memory_id?: number;
      image_url?: string;
      user_vote?: "like" | "dislike" | null;
      local_id?: string;
      meta_data?: {
        localId?: string;
        generated_image?: {
          image_url: string;
          width: number;
          height: number;
          prompt?: string;
          is_matched?: boolean;
          similarity?: number;
          matched_from_user_id?: string;
          model?: string;
          generation_time_ms?: number;
        };
      };
    }>;
    pagination: {
      total: number;
      limit: number;
      offset: number;
      page: number;
      has_more: boolean;
      total_pages: number;
    };
  }> => apiClient.get(`/chats/agents/${agentId}/detail`, params),

  // 获取智能体聊天设置
  getAgentSettings: (
    agentId: string,
  ): Promise<{ premium_mode?: boolean; [key: string]: unknown }> =>
    apiClient.get(`/chats/agents/${agentId}/settings`),

  // 获取对话模式列表（可按 agent 过滤）
  getModes: (agentId?: string | null): Promise<ChatModeOptionCompat[]> =>
    apiClient.get("/chats/modes", agentId ? { agent_id: agentId } : undefined),

  // 获取轻量级消息列表（后端使用 limit/offset；此处兼容 page/size 并转换）
  getMessages: (
    agentId: string,
    params?: {
      page?: number;
      size?: number;
      limit?: number;
      offset?: number;
    },
  ): Promise<{
    messages: Array<{
      id: number;
      role: "user" | "assistant" | null;
      sender_type?: "USER" | "AI" | null;
      content: string;
      timestamp: string;
      created_at?: string;
      type?: "text" | "image" | "festival_memory_prompt" | "surprise_snap";
      festival_memory_id?: number;
      image_url?: string;
      media_url?: string;
      caption?: string;
      price?: number;
      is_locked?: boolean;
      user_vote?: "like" | "dislike" | null;
      local_id?: string;
      meta_data?: {
        localId?: string;
        generated_image?: {
          image_url: string;
          width: number;
          height: number;
          prompt?: string;
          is_matched?: boolean;
          similarity?: number;
          matched_from_user_id?: string;
          model?: string;
          generation_time_ms?: number;
        };
      };
    }>;
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
    page: number;
  }> => {
    const size = params?.size ?? params?.limit ?? 100;
    const page = params?.page ?? 1;
    const limit = params?.limit ?? size;
    const offset = params?.offset ?? (page - 1) * size;
    return apiClient.get(`/chats/agents/${agentId}/messages`, {
      limit,
      offset,
    });
  },

  // 更新消息投票
  updateMessageVote: (
    agentId: string,
    messageId: number,
    vote: "like" | "dislike" | null,
  ): Promise<{
    code: number;
    message: string;
    data: {
      vote: "like" | "dislike" | null;
    };
  }> =>
    apiClient.post(`/chats/messages/vote`, {
      agent_id: agentId,
      message_id: messageId,
      vote,
    }),

  // Surprise Snap 解锁（免费用户用 credit 解锁，扣费在 App 端；后端仅记录解锁状态）
  surpriseSnapUnlock: (
    messageId: number,
  ): Promise<{ data?: { unlocked?: boolean } }> =>
    apiClient.post(`/chats/surprise-snap/unlock`, { message_id: messageId }),

  // 清除聊天消息 - 注意：API 期望单个 message_id 而不是数组
  clearMessages: (
    agentId: string,
    messageId: string,
  ): Promise<{
    message: string;
    cleared_count: number;
  }> =>
    apiClient.post(`/chats/agents/${agentId}/clear-messages`, {
      message_id: parseInt(messageId),
      timestamp: undefined, // Always use message_id approach
    }),

  // 删除聊天会话
  deleteChat: (chatId: string): Promise<{ message: string }> =>
    apiClient.delete(`/chats/${chatId}`),

  // 获取智能体调试消息
  getAgentDebugMessages: (
    agentId: string,
  ): Promise<{ messages?: unknown[]; [key: string]: unknown }> =>
    apiClient.get(`/chats/agents/${agentId}/debug-messages`),

  // 生成消息语音
  generateVoice: (
    agentId: string,
    messageId: string,
    language: string = "zh",
  ): Promise<{
    audio_url: string;
    message_id: string;
    voice_id: string;
    language: string;
    cached: boolean;
    generation_time: number | null;
  }> =>
    apiClient.post(
      `/chats/agents/${agentId}/messages/${messageId}/voice?language=${language}`,
      {},
    ),

  // 更新智能体聊天设置
  updateAgentSettings: (
    agentId: string,
    settings: {
      premium_mode?: boolean;
      language?: string;
      voice_enabled?: boolean;
      style_prompt?: string;
      chat_mode?: string | null;
    },
  ): Promise<{ [key: string]: unknown }> =>
    apiClient.put(`/chats/agents/${agentId}/settings`, settings),
};

// =============================================================================
// 用户管理API - 用于提示词查询功能
// =============================================================================

export const userApi = {
  // 获取当前用户信息
  me: (): Promise<Record<string, unknown>> => apiClient.get("/users/me"),

  // 搜索用户列表
  searchUsers: (params?: {
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<{
    users: Array<{
      id: string;
      readable_id: string;
      nickname: string;
      avatar?: string;
      email?: string;
      phone?: string;
      created_at?: string;
    }>;
    total: number;
  }> => apiClient.get("/users", params),

  // 获取用户列表
  getUsers: (params?: {
    skip?: number;
    limit?: number;
    search?: string;
  }): Promise<
    Array<{
      id: string;
      readable_id: string;
      nickname: string;
      avatar?: string;
      email?: string;
      phone?: string;
      created_at?: string;
    }>
  > => apiClient.get("/users", params),
};

// =============================================================================
// 图片生成API
// =============================================================================

export const imageApi = {
  // 文本生成图片 - 使用与 Inty SDK 相同的认证方式
  textToImage: (data: {
    prompt: string;
    negative_prompt?: string;
    enhance_prompt?: boolean;
    count?: number;
  }): Promise<{
    urls: string[];
    count: number;
    format: string;
    remaining_usage: {
      used_count: number;
      limit: number;
    };
    rai_filtered_count?: number;
    rai_reasons?: string[];
  }> => apiClient.post("/ai/agents/text-to-image", data),
};

// =============================================================================
// 聊天图片生成API
// =============================================================================

export const chatImageApi = {
  // 生成聊天图片
  generateImage: (
    agentId: string,
    data: {
      message_id: number; // 必填：要生成图片的消息ID
      history_count?: number;
      request_id?: string;
    },
  ): Promise<{
    image_url: string;
    image_metadata: {
      width: number;
      height: number;
      format: string;
    };
    prompt: string;
    message_id: number;
    model?: string;
    generation_time_ms?: number;
  }> => apiClient.post(`/chat/images/${agentId}`, data),

  // 获取图片生成配置（模型为 models_catalog nickname）
  getConfig: (): Promise<{
    prompt_template: string;
    default_history_count: number;
    free_user_chat_image_model: string;
    sub_user_chat_image_model: string;
  }> => apiClient.get("/ai/agents/image-generation/config"),

  // 更新图片生成配置（仅超级用户）
  updateConfig: (config: {
    prompt_template?: string;
    default_history_count?: number;
    free_user_chat_image_model?: string;
    sub_user_chat_image_model?: string;
  }): Promise<{
    prompt_template: string;
    default_history_count: number;
    free_user_chat_image_model: string;
    sub_user_chat_image_model: string;
  }> => apiClient.put("/ai/agents/image-generation/config", config),
};

// =============================================================================
// 角色主题专区管理API
// =============================================================================

// =============================================================================
// 生成图片管理API
// =============================================================================

export const generatedImagesApi = {
  // 获取指定角色的生成图片列表
  getAgentImages: (
    agentId: string,
    params?: {
      skip?: number;
      limit?: number;
    },
  ): Promise<import("../types").GeneratedImagesResponse> =>
    apiClient.get(`/evaluation/agents/${agentId}/generated-images`, params),

  // 获取所有角色的图片数量
  getImageCounts: (): Promise<import("../types").ImageCountsResponse> =>
    apiClient.get("/evaluation/agents/generated-images/counts"),
};

// =============================================================================
// 举报与反馈管理API
// =============================================================================

export const reportApi = {
  // 获取举报/反馈列表
  list: (params?: {
    target_type?: import("../types").ReportTargetType;
    target_id?: string;
    status?: import("../types").ReportStatus;
    report_type?: import("../types").ReportType;
    order_by?: "created_at_desc" | "created_at_asc";
    skip?: number;
    limit?: number;
  }): Promise<import("../types").ReportsListResponse> =>
    apiClient.get("/report/", params),

  // 按 id 获取单条举报详情（用于永久链接）
  get: (reportId: string): Promise<import("../types").ReportItem> =>
    apiClient.get(`/report/${reportId}`),

  // 获取某条举报对应举报人的 user_id:agent_id 聊天分组
  getConversationGroups: (
    reportId: string,
  ): Promise<import("../types").ReportConversationGroupsResponse> =>
    apiClient.get(`/report/${reportId}/conversation-groups`),

  // 获取某个 user_id:agent_id 分组内按轮次分页的聊天消息
  getConversationMessages: (params: {
    report_id: string;
    user_id: string;
    agent_id: string;
    page?: number;
    size?: number;
  }): Promise<import("../types").ReportConversationMessagesResponse> =>
    apiClient.get(`/report/${params.report_id}/conversation-messages`, {
      user_id: params.user_id,
      agent_id: params.agent_id,
      page: params.page,
      size: params.size,
    }),

  // 创建举报/反馈记录（聊天图片反馈复用该接口）
  create: (payload: {
    target_id: string;
    target_type: import("../types").ReportTargetType;
    reason_codes: string[];
    image_urls?: string[];
    description?: string;
    report_type?: import("../types").ReportType;
  }): Promise<null> => apiClient.post("/report/", payload),

  // 更新举报/反馈关联的 GitHub issue 链接
  updateGithubIssue: (
    reportId: string,
    githubIssueUrl: string | null,
  ): Promise<import("../types").ReportItem> =>
    apiClient.put(`/report/${reportId}/github-issue`, {
      github_issue: githubIssueUrl,
    }),

  // 删除举报/反馈记录
  delete: (reportId: string): Promise<null> =>
    apiClient.delete(`/report/${reportId}`),
};

export const characterThemeApi = {
  // 获取专区列表
  list: (params?: {
    skip?: number;
    limit?: number;
    include_hidden?: boolean;
  }): Promise<CharacterTheme[]> => apiClient.get("/character-themes/", params), // 添加末尾斜杠以避免 307 重定向

  // 获取专区详情
  get: (themeId: string): Promise<CharacterTheme> =>
    apiClient.get(`/character-themes/${themeId}`),

  // 创建专区
  create: (data: CharacterThemeCreateRequest): Promise<CharacterTheme> =>
    apiClient.post("/character-themes/", data), // 添加末尾斜杠以避免 307 重定向

  // 更新专区
  update: (
    themeId: string,
    data: CharacterThemeUpdateRequest,
  ): Promise<CharacterTheme> =>
    apiClient.put(`/character-themes/${themeId}`, data),

  // 删除专区
  delete: (themeId: string): Promise<{ message: string }> =>
    apiClient.delete(`/character-themes/${themeId}`),

  // 添加角色到专区
  addAgent: (
    themeId: string,
    data: AddAgentToThemeRequest,
  ): Promise<CharacterThemeAgent> =>
    apiClient.post(`/character-themes/${themeId}/agents`, data),

  // 从专区移除角色
  removeAgent: (
    themeId: string,
    agentId: string,
  ): Promise<{ message: string }> =>
    apiClient.delete(`/character-themes/${themeId}/agents/${agentId}`),

  // 调整角色顺序
  reorderAgents: (
    themeId: string,
    data: ReorderAgentsRequest,
  ): Promise<{ message: string }> =>
    apiClient.put(`/character-themes/${themeId}/agents/reorder`, data),
};

// =============================================================================
// 节日记忆配置与抽取（管理员）
// =============================================================================

export const festivalMemoryApi = {
  listConfigs: (params?: {
    skip?: number;
    limit?: number;
  }): Promise<import("../types").FestivalMemoryConfigItem[]> =>
    apiClient.get("/evaluation/admin/festival-memory-configs", params),

  createConfig: (
    data: import("../types").FestivalMemoryConfigCreate,
  ): Promise<import("../types").FestivalMemoryConfigItem> =>
    apiClient.post("/evaluation/admin/festival-memory-configs", data),

  updateConfig: (
    configId: number,
    data: import("../types").FestivalMemoryConfigUpdate,
  ): Promise<import("../types").FestivalMemoryConfigItem> =>
    apiClient.put(
      `/evaluation/admin/festival-memory-configs/${configId}`,
      data,
    ),

  deleteConfig: (configId: number): Promise<null> =>
    apiClient.delete(`/evaluation/admin/festival-memory-configs/${configId}`),

  runExtraction: (
    body: import("../types").FestivalMemoryExtractionRunRequest,
  ): Promise<import("../types").FestivalMemoryExtractionRunResponse> =>
    apiClient.post("/evaluation/admin/festival-memory-extraction/run", body),
};

// =============================================================================
// 导出默认API实例
// =============================================================================

export default {
  sessions: evaluationSessionApi,
  agents: agentApi,
  templates: templateApi,
  questions: questionApi,
  scoring: scoringApi,
  stats: statsApi,
  subscription: subscriptionApi,
  chat: chatApi,
  users: userApi,
  characterThemes: characterThemeApi,
  voices: voiceApi,
  images: imageApi,
  chatImage: chatImageApi,
  userAnalytics: userAnalyticsApi,
  generatedImages: generatedImagesApi,
  report: reportApi,
  festivalMemory: festivalMemoryApi,
  WebSocketManager,
};
