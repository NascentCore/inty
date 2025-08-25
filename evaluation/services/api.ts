/**
 * 此处代码是评测系统调用 Inty 后端 API
 */

import type {
  Agent,
  AgentCreateRequest,
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

class ApiClient {
  private baseURL: string;
  private headers: Record<string, string>;

  constructor(
    baseURL: string = process.env.REACT_APP_API_BASE_URL || "/api/v1",
  ) {
    this.baseURL = baseURL;
    // This is the default headers for all requests.
    // Some API endpoints needs different content header, like upload avatar,
    // needs multipart/form-data.
    this.headers = {
      "Content-Type": "application/json",
    };
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;

    const config: RequestInit = {
      ...options,
      headers: {
        ...this.headers,
        ...options.headers,
      },
    };

    // 如果是上传请求（FormData），不要覆盖Content-Type
    if (options.body instanceof FormData) {
      config.headers = {
        ...options.headers, // 优先使用传入的headers
        ...this.headers, // 然后合并默认headers（除了Content-Type）
      };
      // 删除Content-Type，让浏览器自动设置；覆盖默认的 Content-Type: application/json
      // TODO: 是否仅支持浏览器使用，代码中使用该 API 是否会有问题
      if (config.headers && typeof config.headers === "object") {
        delete (config.headers as any)["Content-Type"];
      }
    }

    // 添加认证token
    const token = this.getAuthToken();
    if (token) {
      config.headers = {
        ...config.headers,
        Authorization: `Bearer ${token}`,
      };
    }

    try {
      const response = await fetch(url, config);

      class ApiError extends Error {
        public status: number;
        public statusText: string;
        public errorData: any;

        constructor(
          message: string,
          status: number,
          statusText: string,
          errorData: any,
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
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
          errorData.detail ||
          errorData.message ||
          `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          response.statusText,
          errorData,
        );
      }

      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        const result = await response.json();

        // Log the complete response from backend
        console.log("=== FULL BACKEND RESPONSE ===");
        console.log("Endpoint:", endpoint);
        console.log("HTTP Status:", response.status, response.statusText);
        console.log("Content-Type:", contentType);
        console.log("Response Headers:", Object.fromEntries(response.headers.entries()));
        console.log("Raw Response Body:", result);

        // Check if it's APIResponse format
        if (result && typeof result === "object" && "code" in result) {
          console.log("APIResponse Structure:");
          console.log("  - code:", result.code);
          console.log("  - message:", result.message);
          console.log("  - data:", result.data);

          if (result.code === 200) {
            console.log("✅ Success Response - returning data field");
            return result.data;
          } else {
            console.log("❌ Error Response - throwing exception");
            throw new ApiError(
              result.message || "API Error",
              response.status,
              response.statusText,
              result
            );
          }
        } else {
          console.log("⚠️ Non-APIResponse format - returning raw result");
          return result;
        }
      } else {
        // Log non-JSON responses
        console.log("=== NON-JSON RESPONSE ===");
        console.log("Endpoint:", endpoint);
        console.log("HTTP Status:", response.status, response.statusText);
        console.log("Content-Type:", contentType);
        console.log("Response Headers:", Object.fromEntries(response.headers.entries()));
        console.log("Response is not JSON, returning response object");
        return response as any;
      }
    } catch (error) {
      logError(`API请求失败: ${endpoint}, 错误信息: ${error}`);
      throw error;
    }
  }

  private getAuthToken(): string | null {
    // 默认使用管理员token，与inty-test项目保持一致
    // 这是从inty-test/backend/config.yaml中配置的default_token
    const adminToken =
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODQzNjAyMjAsInN1YiI6InVzZXItMDFKV1ozNFk0RDFDOTJHRDg2QTVSNkVXWUoifQ.vsYKRvrCfxWgJ5wkTjAYby3RrIOm6P-9VbcCg4msjlM";
    return adminToken;
  }

  // GET请求
  async get<T>(
    endpoint: string,
    params?: Record<string, any>,
    options?: RequestInit,
  ): Promise<T> {
    let finalEndpoint = endpoint;

    if (params && !("signal" in params)) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
      const queryString = searchParams.toString();
      if (queryString) {
        finalEndpoint += `?${queryString}`;
      }
    }

    return this.request<T>(finalEndpoint, { method: "GET", ...options });
  }

  // POST请求
  async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // PUT请求
  async put<T>(endpoint: string, data?: any): Promise<T> {
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
    additionalData?: Record<string, any>,
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
const apiClient = new ApiClient();

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

export const agentApi = {
  // 获取智能体列表 - 使用现有的agents API（注意路径是 /ai/agents）
  list: (params?: {
    type?: "public" | "private";
    skip?: number;
    limit?: number;
  }): Promise<Agent[]> => apiClient.get("/ai/agents/", params),

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
    apiClient.post("/ai/agents/", data),

  // 更新智能体 - 使用现有API
  update: (
    agentId: string,
    data: Partial<AgentUpdateRequest>,
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
  uploadAvatar: (file: File): Promise<any> =>
    apiClient.upload("/ai/agents/upload-avatar", file),
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
      return models;
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
// WebSocket连接管理
// =============================================================================

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 3000;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

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
            const message = JSON.parse(event.data);
            this.handleMessage(message);
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

  private handleMessage(message: any) {
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

  on(eventType: string, callback: (data: any) => void) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)!.add(callback);
  }

  off(eventType: string, callback: (data: any) => void) {
    const listeners = this.listeners.get(eventType);
    if (listeners) {
      listeners.delete(callback);
    }
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
      content: string;
    }>,
    stream: boolean = false,
  ): Promise<{
    id: string;
    object: string;
    created: number;
    model: string;
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
  }> =>
    apiClient.post(`/chats/agents/${agentId}/chat/completions`, {
      messages,
      stream,
      model: "chatbot",
      language: "zh",
    }),

  // 获取Agent聊天详情和消息历史
  getChatDetail: (
    agentId: string,
    params?: {
      page?: number;
      size?: number;
    },
  ): Promise<{
    chat: {
      id: string;
      agent_id: string;
      user_id: string;
      is_active: boolean;
      created_at: string;
      updated_at: string;
    };
    agent: {
      id: string;
      name: string;
      avatar?: string;
      description?: string;
    };
    messages: Array<{
      content: string;
      sender_type: "USER" | "AI";
      created_at: string;
    }>;
    total: number;
    page: number;
    size: number;
    has_more: boolean;
  }> => apiClient.get(`/chats/agents/${agentId}/detail`, params),

  // 获取轻量级消息列表
  getMessages: (
    agentId: string,
    params?: {
      page?: number;
      size?: number;
    },
  ): Promise<{
    messages: Array<{
      id: number;
      role: "user" | "assistant";
      content: string;
      timestamp: string;
    }>;
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
    page: number;
  }> => apiClient.get(`/chats/agents/${agentId}/messages`, params),

  // 清除聊天消息 - 注意：API 期望单个 message_id 而不是数组
  clearMessages: (
    agentId: string,
    messageId?: string,
  ): Promise<{
    message: string;
    cleared_count: number;
  }> =>
    apiClient.post(`/chats/agents/${agentId}/clear-messages`, {
      message_id: messageId ? parseInt(messageId) : 2, // Use message ID 2 instead of old timestamp
      timestamp: undefined, // Always use message_id approach
    }),

  // 删除聊天会话
  deleteChat: (chatId: string): Promise<{ message: string }> =>
    apiClient.delete(`/chats/${chatId}`),

  // 获取智能体调试消息
  getAgentDebugMessages: (agentId: string): Promise<any> =>
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
};

// =============================================================================
// 用户管理API - 用于提示词查询功能
// =============================================================================

export const userApi = {
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
// 导出默认API实例
// =============================================================================

export default {
  sessions: evaluationSessionApi,
  agents: agentApi,
  templates: templateApi,
  questions: questionApi,
  scoring: scoringApi,
  stats: statsApi,
  chat: chatApi,
  users: userApi,
  WebSocketManager,
};
