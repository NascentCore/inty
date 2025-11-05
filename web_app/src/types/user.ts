/**
 * 用户相关类型定义
 */

/**
 * 用户性别枚举
 */
export type TUserGender = 'MALE' | 'FEMALE' | 'OTHER';

/**
 * 用户认证类型
 */
export type TUserAuthType = 'PHONE' | 'GOOGLE' | 'GUEST';

/**
 * 用户信息接口（简化版）
 */
export interface IUserInfo {
  /** 用户 ID */
  id: string;
  /** 用户名 */
  username: string;
  /** 昵称 */
  nickname?: string;
  /** 头像 URL */
  avatar?: string;
  /** 邮箱 */
  email?: string;
  /** 手机号 */
  phone?: string;
}

/**
 * 用户详细信息接口（来自 SDK API）
 */
export interface IUserProfile {
  /** 用户 ID */
  id: string;
  /** 认证类型 */
  auth_type: TUserAuthType;
  /** 创建时间 */
  created_at: string;
  /** 是否激活 */
  is_active: boolean;
  /** 可读 ID */
  readable_id: string;
  /** 年龄组 */
  age_group?: string | null;
  /** 头像 URL */
  avatar?: string | null;
  /** 连接数 */
  connector_count?: number | null;
  /** 个人简介 */
  description?: string | null;
  /** 邮箱 */
  email?: string | null;
  /** 关注者数量 */
  followers_count?: number | null;
  /** 性别 */
  gender?: TUserGender | null;
  /** 是否超级用户 */
  is_superuser?: boolean;
  /** 昵称 */
  nickname?: string | null;
  /** 手机号 */
  phone?: string | null;
  /** 公开 Agent 数量 */
  public_agents_count?: number | null;
  /** 系统语言 */
  system_language?: string | null;
  /** 公开 Agent 关注总数 */
  total_public_agents_follows?: number | null;
  /** 更新时间 */
  updated_at?: string | null;
}
