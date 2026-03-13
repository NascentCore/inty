/**
 * 订阅相关 API 服务
 * 使用手写 HTTP wrapper 实现（非 Inty SDK）
 */

import type { ISubscriptionPlansData } from '@/types';
import { getToken } from '@/utils/token';

interface IApiResult<T> {
  code?: number;
  message?: string;
  data?: T | null;
}

const SUBSCRIPTION_PLANS_PATH = '/api/v1/subscription/plans';

/**
 * 获取订阅计划列表
 * 通过手写 HTTP 请求访问后端，而非 SDK
 * @returns 订阅计划数据
 * @throws 当 token 缺失、网络失败或响应异常时抛出错误
 */
export async function getSubscriptionPlans(): Promise<ISubscriptionPlansData> {
  const token = await getToken();
  if (!token) {
    throw new Error('未找到 Token，请先登录');
  }

  const response = await fetch(SUBSCRIPTION_PLANS_PATH, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch subscription plans (HTTP ${response.status})`);
  }

  const result = (await response.json()) as IApiResult<ISubscriptionPlansData>;
  if (result.code !== 200 || !result.data) {
    throw new Error(result.message || 'Failed to fetch subscription plans');
  }

  return result.data;
}
