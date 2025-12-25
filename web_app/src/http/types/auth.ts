/**
 * 认证相关类型
 */

/**
 * 访客登录请求参数
 */
export interface GuestLoginRequest {
  device_id: string;
  system_language?: string;
  age_group?: string;
  request_id?: string;
}

/**
 * 访客登录响应数据
 */
export interface GuestLoginData {
  token: string;
  guest_id: string;
  is_new_guest: boolean;
}
