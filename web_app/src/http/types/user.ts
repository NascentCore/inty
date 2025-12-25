/**
 * 用户相关类型
 */

/**
 * 用户资料更新参数
 */
export interface UpdateProfileRequest {
  nickname?: string;
  avatar_url?: string;
  age_group?: string;
  gender?: string;
  bio?: string;
}
