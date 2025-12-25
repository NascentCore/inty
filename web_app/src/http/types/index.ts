/**
 * HTTP 请求类型定义
 */

import type { AxiosRequestConfig } from 'axios';

/**
 * 通用 API 响应结构
 */
export interface ApiResult<T = any> {
  code: number;
  message: string;
  data: T;
}

/**
 * HTTP 方法类型
 */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

/**
 * 扩展的请求配置，支持无需认证的请求
 */
export interface RequestConfig extends AxiosRequestConfig {
  skipAuth?: boolean;
}

/**
 * API 错误响应结构
 */
export interface ApiErrorResponse {
  code?: number;
  message?: string;
  data?: any;
}
