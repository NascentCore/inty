/**
 * 认证相关 API
 */

import request from '../request';
import type { ApiResult } from '../types/index';
import type { GuestLoginRequest, GuestLoginData } from '../types/auth';

/**
 * 访客登录
 */
export function guestLogin(params: GuestLoginRequest): Promise<ApiResult<GuestLoginData>> {
  return request.post('/api/v1/auth/guest', params);
}
