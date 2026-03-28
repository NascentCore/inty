/**
 * 本地 HTTP 客户端统一配置工具（替代 Inty SDK）
 * 提供与历史 client.api.v1.* 兼容的调用结构
 */

import { INTY_SDK_CONFIG } from '@/constants';
import { getToken } from './token';

export class HttpClientError extends Error {
  status?: number;
  data?: unknown;

  constructor(message: string, status?: number, data?: unknown) {
    super(message);
    this.name = 'HttpClientError';
    this.status = status;
    this.data = data;
  }
}

export class AuthenticationError extends HttpClientError {
  constructor(message: string, status?: number, data?: unknown) {
    super(message, status, data);
    this.name = 'AuthenticationError';
  }
}

export class NotFoundError extends HttpClientError {
  constructor(message: string, status?: number, data?: unknown) {
    super(message, status, data);
    this.name = 'NotFoundError';
  }
}

export class PermissionDeniedError extends HttpClientError {
  constructor(message: string, status?: number, data?: unknown) {
    super(message, status, data);
    this.name = 'PermissionDeniedError';
  }
}

interface IApiRequestOptions {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  path: string;
  token?: string;
  query?: Record<string, unknown>;
  body?: unknown;
  headers?: Record<string, string>;
  formData?: FormData;
}

interface IIntyLikeClient {
  v2: {
    chat: {
      sendMessage: (
        agentId: string,
        params: Record<string, unknown>,
      ) => Promise<{ data: any }>;
    };
  };
  api: {
    v1: {
      auth: {
        createGuest: (params: unknown) => Promise<any>;
        google: {
          login: (params: unknown) => Promise<any>;
        };
      };
      ai: {
        agents: {
          list: (params?: Record<string, unknown>) => Promise<any>;
          retrieve: (agentId: string) => Promise<any>;
          recommend: (params?: Record<string, unknown>) => Promise<any>;
          search: (params: Record<string, unknown>) => Promise<any>;
          create: (params: Record<string, unknown>) => Promise<any>;
          update: (agentId: string, params: Record<string, unknown>) => Promise<any>;
          delete: (agentId: string) => Promise<any>;
          followAgent: (_agentId: string) => Promise<any>;
          unfollowAgent: (_agentId: string) => Promise<any>;
          following: (_params?: Record<string, unknown>) => Promise<any>;
        };
      };
      chats: {
        list: (params?: Record<string, unknown>) => Promise<any>;
        create: (params: Record<string, unknown>) => Promise<any>;
        delete: (chatId: string) => Promise<any>;
        createCompletion: (agentId: string, params: Record<string, unknown>) => Promise<any>;
        agents: {
          getMessages: (agentId: string, params?: Record<string, unknown>) => Promise<any>;
          generateMessageVoice: (
            messageId: string,
            params: { agent_id: string; language?: string },
          ) => Promise<any>;
          getSettings: (agentId: string) => Promise<any>;
          updateSettings: (agentId: string, params: Record<string, unknown>) => Promise<any>;
        };
      };
      users: {
        profile: {
          me: () => Promise<any>;
          update: (params: Record<string, unknown>) => Promise<any>;
        };
        deleteAccount: (params?: Record<string, unknown>) => Promise<any>;
      };
      subscription: {
        listPlans: () => Promise<any>;
        getStatus: () => Promise<any>;
        getUsage: () => Promise<any>;
        verify: (params: Record<string, unknown>) => Promise<any>;
      };
      settings: {
        retrieve: () => Promise<any>;
        update: (params: Record<string, unknown>) => Promise<any>;
      };
      version: {
        check: (params: { appVersionCode: number; appVersionName?: string }) => Promise<any>;
      };
      textToSpeech: {
        listVoices: (params?: Record<string, unknown>) => Promise<any>;
      };
      report: {
        create: (params: Record<string, unknown>) => Promise<any>;
      };
      uploadImage: (params: { file: File; cropping_avatar?: boolean }) => Promise<any>;
      listNotifications: (params?: Record<string, unknown>) => Promise<any>;
    };
  };
}

/**
 * 获取当前环境的 Base URL
 * 统一使用相对路径 '/'，通过代理配置转发到实际服务器
 * - 开发环境: 通过 proxy.ts 转发到 https://dev.inty.sxwl.ai
 * - 生产环境: 直接请求到生产服务器
 */
function getBaseURL(): string {
  return INTY_SDK_CONFIG.BASE_URL;
}

function buildUrl(path: string, query?: Record<string, unknown>): string {
  const base = getBaseURL();
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = new URL(normalizedPath, base);

  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') {
        return;
      }
      url.searchParams.set(key, String(value));
    });
  }

  return url.toString();
}

function mapHttpError(status: number, message: string, data?: unknown): HttpClientError {
  if (status === 401) {
    return new AuthenticationError(message, status, data);
  }
  if (status === 403) {
    return new PermissionDeniedError(message, status, data);
  }
  if (status === 404) {
    return new NotFoundError(message, status, data);
  }
  return new HttpClientError(message, status, data);
}

async function request<T = any>(options: IApiRequestOptions): Promise<T> {
  const { method, path, token, query, body, headers, formData } = options;

  const requestHeaders: Record<string, string> = {
    Accept: 'application/json',
    ...(headers || {}),
  };

  if (token) {
    requestHeaders.Authorization = `Bearer ${token}`;
  }

  const init: RequestInit = {
    method,
    headers: requestHeaders,
  };

  if (formData) {
    // multipart/form-data 交给浏览器自动注入边界
    delete requestHeaders['Content-Type'];
    init.body = formData;
  } else if (body !== undefined) {
    requestHeaders['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), init);
  } catch (error) {
    throw new HttpClientError(
      error instanceof Error ? error.message : 'Network request failed',
    );
  }

  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const payload = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    const message =
      (typeof payload === 'object' &&
        payload &&
        ('message' in payload || 'detail' in payload) &&
        String((payload as { message?: string; detail?: string }).message || (payload as { detail?: string }).detail)) ||
      `HTTP ${response.status}`;
    throw mapHttpError(response.status, message, payload);
  }

  return payload as T;
}

/**
 * 创建本地 HTTP 客户端实例
 * @param requireAuth - 是否必须有 token（默认 false）
 * @returns 兼容 Inty SDK 调用结构的客户端实例
 * @throws 当 requireAuth 为 true 但没有 token 时抛出错误
 *
 * @example
 * // 无需认证（如访客登录）
 * const client = await createIntyClient();
 *
 * // 需要认证（如获取用户信息）
 * const client = await createIntyClient(true);
 */
export async function createIntyClient(requireAuth = false): Promise<IIntyLikeClient> {
  const token = await getToken();

  if (requireAuth && !token) {
    throw new Error('未找到 Token，请先登录');
  }

  const authToken = token || '';

  return {
    v2: {
      chat: {
        sendMessage: async (agentId, params) => {
          const data = await request({
            method: 'POST',
            path: `/api/v1/chat/completions/${agentId}`,
            token: authToken,
            body: params,
          });
          return { data };
        },
      },
    },
    api: {
      v1: {
        auth: {
          createGuest: (params) =>
            request({
              method: 'POST',
              path: '/api/v1/auth/guest',
              body: params,
            }),
          google: {
            login: (params) =>
              request({
                method: 'POST',
                path: '/api/v1/auth/google/login',
                body: params,
              }),
          },
        },
        ai: {
          agents: {
            list: (params) =>
              request({
                method: 'GET',
                path: '/api/v1/ai/agents/me',
                token: authToken,
                query: params,
              }),
            retrieve: (agentId) =>
              request({
                method: 'GET',
                path: `/api/v1/ai/agents/${agentId}`,
                token: authToken,
              }),
            recommend: (params) =>
              request({
                method: 'GET',
                path: '/api/v1/ai/agents/recommend',
                token: authToken,
                query: params,
              }),
            search: (params) =>
              request({
                method: 'GET',
                path: '/api/v1/ai/agents/search',
                token: authToken,
                query: params,
              }),
            create: (params) =>
              request({
                method: 'POST',
                path: '/api/v1/ai/agents',
                token: authToken,
                body: params,
              }),
            update: (agentId, params) =>
              request({
                method: 'PUT',
                path: `/api/v1/ai/agents/${agentId}`,
                token: authToken,
                body: params,
              }),
            delete: (agentId) =>
              request({
                method: 'DELETE',
                path: `/api/v1/ai/agents/${agentId}`,
                token: authToken,
              }),
            // 后端暂无同名 endpoint，保持兼容结构并显式失败
            followAgent: async (_agentId: string) => {
              throw new NotFoundError('Follow agent endpoint is not available in backend', 404);
            },
            // 后端暂无同名 endpoint，保持兼容结构并显式失败
            unfollowAgent: async (_agentId: string) => {
              throw new NotFoundError('Unfollow agent endpoint is not available in backend', 404);
            },
            // 后端暂无同名 endpoint，保持兼容结构并显式失败
            following: async (_params?: Record<string, unknown>) => {
              throw new NotFoundError('Following endpoint is not available in backend', 404);
            },
          },
        },
        chats: {
          list: (params) =>
            request({
              method: 'GET',
              path: '/api/v1/chats/',
              token: authToken,
              query: params,
            }),
          create: (params) =>
            request({
              method: 'POST',
              path: '/api/v1/chats/',
              token: authToken,
              body: params,
            }),
          delete: (chatId) =>
            request({
              method: 'DELETE',
              path: `/api/v1/chats/${chatId}`,
              token: authToken,
            }),
          createCompletion: (agentId, params) =>
            request({
              method: 'POST',
              path: `/api/v1/chat/completions/${agentId}`,
              token: authToken,
              body: params,
            }),
          agents: {
            getMessages: (agentId, params) =>
              request({
                method: 'GET',
                path: `/api/v1/chats/agents/${agentId}/messages`,
                token: authToken,
                query: params,
              }),
            generateMessageVoice: (messageId, params) =>
              request({
                method: 'POST',
                path: `/api/v1/chats/agents/${params.agent_id}/messages/${messageId}/voice`,
                token: authToken,
                query: params.language ? { language: params.language } : undefined,
              }),
            getSettings: (agentId) =>
              request({
                method: 'GET',
                path: `/api/v1/chats/agents/${agentId}/settings`,
                token: authToken,
              }),
            updateSettings: (agentId, params) =>
              request({
                method: 'PUT',
                path: `/api/v1/chats/agents/${agentId}/settings`,
                token: authToken,
                body: params,
              }),
          },
        },
        users: {
          profile: {
            me: () =>
              request({
                method: 'GET',
                path: '/api/v1/users/me',
                token: authToken,
              }),
            update: (params) =>
              request({
                method: 'PUT',
                path: '/api/v1/users/profile',
                token: authToken,
                body: params,
              }),
          },
          deleteAccount: (params) =>
            request({
              method: 'POST',
              path: '/api/v1/users/delete-account',
              token: authToken,
              body: params || {},
            }),
        },
        subscription: {
          listPlans: () =>
            request({
              method: 'GET',
              path: '/api/v1/subscription/plans',
              token: authToken,
            }),
          getStatus: () =>
            request({
              method: 'GET',
              path: '/api/v1/subscription/status',
              token: authToken,
            }),
          getUsage: () =>
            request({
              method: 'GET',
              path: '/api/v1/subscription/usage',
              token: authToken,
            }),
          verify: (params) =>
            request({
              method: 'POST',
              path: '/api/v1/subscription/verify',
              token: authToken,
              body: params,
            }),
        },
        settings: {
          retrieve: () =>
            request({
              method: 'GET',
              path: '/api/v1/settings/',
              token: authToken,
            }),
          update: (params) =>
            request({
              method: 'PUT',
              path: '/api/v1/settings/',
              token: authToken,
              body: params,
            }),
        },
        version: {
          check: (params) =>
            request({
              method: 'POST',
              path: '/api/v1/version/check',
              token: authToken,
              headers: {
                appVersionCode: String(params.appVersionCode),
                ...(params.appVersionName ? { appVersionName: params.appVersionName } : {}),
              },
            }),
        },
        textToSpeech: {
          listVoices: (params) =>
            request({
              method: 'GET',
              path: '/api/v1/text-to-speech/list-voices',
              token: authToken,
              query: params,
            }),
        },
        report: {
          create: (params) =>
            request({
              method: 'POST',
              path: '/api/v1/report/',
              token: authToken,
              body: params,
            }),
        },
        uploadImage: (params) => {
          const formData = new FormData();
          formData.append('file', params.file);
          if (params.cropping_avatar !== undefined) {
            formData.append('cropping_avatar', String(params.cropping_avatar));
          }
          return request({
            method: 'POST',
            path: '/api/v1/images',
            token: authToken,
            formData,
          });
        },
        listNotifications: (params) =>
          request({
            method: 'GET',
            path: '/api/v1/notifications/',
            token: authToken,
            query: params,
          }),
      },
    },
  };
}
