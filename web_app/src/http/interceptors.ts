/**
 * Axios 拦截器配置
 * 包含请求拦截器和响应拦截器
 */

import type { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import { getToken } from '@/utils/token';
import { logger } from '@/utils';
import type { ApiErrorResponse } from './types/index';

/**
 * 设置拦截器
 */
export function setupInterceptors(instance: AxiosInstance) {
  // 请求拦截器 - 自动注入 token
  instance.interceptors.request.use(
    async (config: InternalAxiosRequestConfig & { skipAuth?: boolean }) => {
      // 如果不是跳过认证的请求，添加 token
      if (!config.skipAuth) {
        const token = await getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
      logger.info('HTTP Request', {
        method: config.method?.toUpperCase(),
        url: config.url,
      });
      return config;
    },
    (error: AxiosError) => {
      logger.error('HTTP Request Error', error);
      return Promise.reject(error);
    }
  );

  // 响应拦截器 - 统一处理响应和错误
  instance.interceptors.response.use(
    (response: AxiosResponse) => {
      logger.info('HTTP Response', {
        status: response.status,
        url: response.config.url,
      });
      // 直接返回响应数据
      return response.data;
    },
    async (error: AxiosError<ApiErrorResponse>) => {
      const { response, request, message } = error;

      logger.error('HTTP Response Error', {
        status: response?.status,
        url: response?.config.url || request?.responseURL,
        message,
        data: response?.data,
      });

      // 处理 401 未授权错误
      if (response?.status === 401) {
        // 可以在这里触发登出逻辑或重新登录
        logger.warn('Unauthorized access, token may be expired');
      }

      // 返回统一的错误格式
      return Promise.reject({
        status: response?.status || 0,
        message: response?.data?.message || message || 'Request failed',
        code: response?.data?.code,
        data: response?.data,
      });
    }
  );
}
