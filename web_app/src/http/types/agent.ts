/**
 * Agent 相关类型
 */

/**
 * SDK 排序类型
 */
export type SortType = 'created_asc' | 'created_desc' | 'random' | 'score_based_random';

/**
 * 获取推荐 Agent 参数
 */
export interface RecommendAgentsParams {
  page?: number;
  page_size?: number;
  sort?: SortType;
  sort_seed?: string;
}

/**
 * 推荐 Agent 响应数据
 */
export interface RecommendAgentsData {
  agents: any[];
  total: number;
  has_more: boolean;
}
