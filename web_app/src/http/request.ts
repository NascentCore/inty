/**
 * Axios 实例配置
 * 提供统一的 HTTP 请求客户端
 */

import axios, { AxiosInstance } from 'axios';
import { setupInterceptors } from './interceptors';
import type { RequestConfig } from './types/index';

/**
 * Base URL
 * 开发环境通过代理转发到 https://dev.inty.sxwl.ai
 * 生产环境直接请求到生产服务器
 */
export const baseURL = '/';

/**
 * 创建 Axios 实例
 */
const instance: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 设置拦截器
setupInterceptors(instance);

/**
 * GET 请求
 */
export function get<T = any>(url: string, config?: RequestConfig): Promise<T> {
  return instance.get(url, config);
}

/**
 * POST 请求
 */
export function post<T = any>(url: string, data?: any, config?: RequestConfig): Promise<T> {
  return instance.post(url, data, config);
}

/**
 * PUT 请求
 */
export function put<T = any>(url: string, data?: any, config?: RequestConfig): Promise<T> {
  return instance.put(url, data, config);
}

/**
 * DELETE 请求
 */
export function del<T = any>(url: string, config?: RequestConfig): Promise<T> {
  return instance.delete(url, config);
}

/**
 * PATCH 请求
 */
export function patch<T = any>(url: string, data?: any, config?: RequestConfig): Promise<T> {
  return instance.patch(url, data, config);
}

export default instance;
