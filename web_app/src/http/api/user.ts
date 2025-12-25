/**
 * 用户相关 API
 */

import request from '../request';
import type { ApiResult } from '../types/index';
import type { UpdateProfileRequest } from '../types/user';

/**
 * 获取当前用户信息
 */
export function getUserProfile<T = any>(): Promise<ApiResult<T>> {
  return request.get('/api/v1/users/me');
}

/**
 * 更新用户资料
 */
export function updateUserProfile<T = any>(data: UpdateProfileRequest): Promise<ApiResult<T>> {
  return request.put('/api/v1/users/me', data);
}
