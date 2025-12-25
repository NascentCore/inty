/**
 * Agent 相关 API
 */

import request from '../request';
import type { ApiResult } from '../types/index';
import type { RecommendAgentsParams, RecommendAgentsData } from '../types/agent';

/**
 * 获取 Agent 详情
 */
export function getAgentDetail<T = any>(agentId: string): Promise<T> {
  return request.get(`/api/v1/ai/agents/${agentId}`);
}

/**
 * 获取推荐 Agent 列表
 */
export function getRecommendAgents(params: RecommendAgentsParams): Promise<ApiResult<RecommendAgentsData>> {
  return request.get('/api/v1/ai/agents/recommend', { params });
}
