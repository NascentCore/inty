/**
 * 订阅相关类型定义
 */

/**
 * 订阅计划类型枚举
 */
export type TSubscriptionPlanType = 'MONTHLY' | 'QUARTERLY' | 'YEARLY';

/**
 * 订阅状态枚举
 */
export type TSubscriptionStatus =
  | 'ACTIVE'
  | 'EXPIRED'
  | 'CANCELLED'
  | 'PENDING'
  | 'REFUNDED'
  | 'GRACE_PERIOD'
  | 'PAUSED';

/**
 * 功能类型枚举
 */
export type TFeatureType = 'real' | 'fake';

/**
 * 订阅功能特性
 */
export interface ISubscriptionFeature {
  /** 功能键名 */
  key: string;
  /** 功能名称 */
  name: string;
  /** 功能描述 */
  description: string;
  /** 功能类型 */
  type: TFeatureType;
  /** 图标 */
  icon: string;
  /** 排序顺序 */
  order: number;
}

/**
 * 订阅功能配置
 */
export interface ISubscriptionFeatures {
  /** 所有功能列表 */
  features: ISubscriptionFeature[];
  /** 真实功能键名列表 */
  real_features: string[];
  /** 虚拟功能键名列表 */
  fake_features: string[];
}

/**
 * 订阅计划
 */
export interface ISubscriptionPlan {
  /** 计划 ID */
  id: string;
  /** 计划名称 */
  name: string;
  /** 计划描述 */
  description?: string | null;
  /** 计划类型 */
  plan_type: TSubscriptionPlanType;
  /** 价格 */
  price: number;
  /** 货币单位 */
  currency: string;
  /** Google Play 产品 ID */
  google_play_product_id: string;
  /** 折扣率 (0-1) */
  discount_rate: number;
  /** 功能特性配置 */
  features: ISubscriptionFeatures;
  /** 每日聊天次数限制 (-1 表示无限制) */
  chat_limit_per_day: number;
  /** Agent 创建数量限制 */
  agent_creation_limit: number;
  /** 每日背景图生成次数限制 (-1 表示无限制) */
  background_generation_limit_per_day: number;
  /** 是否激活 */
  is_active: boolean;
  /** 排序顺序 */
  sort_order: number;
  /** 创建时间 */
  created_at: string;
  /** 更新时间 */
  updated_at: string;
}

/**
 * 用户订阅信息
 */
export interface IUserSubscription {
  /** 订阅 ID */
  id: string;
  /** 用户 ID */
  user_id: string;
  /** 计划 ID */
  plan_id: string;
  /** 创建时间 */
  created_at: string;
  /** 开始时间 */
  start_date?: string | null;
  /** 结束时间 */
  end_date?: string | null;
  /** 试用结束时间 */
  trial_end_date?: string | null;
  /** 是否自动续费 */
  auto_renew?: boolean;
  /** 订阅状态 */
  status?: TSubscriptionStatus;
  /** Google Play 订单 ID */
  google_play_order_id?: string | null;
  /** Google Play 购买令牌 */
  google_play_purchase_token?: string | null;
  /** Google Play 订阅 ID */
  google_play_subscription_id?: string | null;
  /** 额外数据 */
  extra_data?: Record<string, unknown> | null;
  /** 更新时间 */
  updated_at?: string | null;
  /** 关联的订阅计划 */
  plan?: ISubscriptionPlan | null;
}

/**
 * 订阅计划列表响应数据
 */
export interface ISubscriptionPlansData {
  /** 订阅计划列表 */
  plans: ISubscriptionPlan[];
  /** 当前订阅 */
  current_subscription: IUserSubscription | null;
  /** 是否曾经订阅过 */
  has_ever_subscribed: boolean;
  /** 上次订阅的计划 ID */
  previous_plan_id: string | null;
}
