/**
 * AI 角色状态管理
 * 管理 AI 角色列表、推荐、收藏、关注等状态
 */

import { useState, useCallback } from 'react';
import { getRecommendAgents, getAgentDetail } from '@/services/agent';
import type {
  IAgent,
  IAgentRecommendRequest,
  IAgentRecommendData,
} from '@/types';

/**
 * AI 角色 Model 状态接口
 */
export interface IAgentModelState {
  /** 推荐角色列表 */
  recommendList: IAgent[];
  /** 当前选中的角色 */
  currentAgent: IAgent | null;
  /** 列表加载状态 */
  loading: boolean;
  /** Agent 详情加载状态 */
  detailLoading: boolean;
  /** 错误信息 */
  error: string | null;
  /** 分页信息 */
  pagination: {
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
  };
}

export default function useAgentModel() {
  // 状态定义
  const [recommendList, setRecommendList] = useState<IAgent[]>([]);
  const [currentAgent, setCurrentAgent] = useState<IAgent | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState({
    total: 0,
    page: 1,
    pageSize: 20,
    totalPages: 0,
  });

  /**
   * 加载推荐角色列表
   * @param params 请求参数
   */
  const loadRecommendAgents = useCallback(
    async (params?: Partial<IAgentRecommendRequest>) => {
      setLoading(true);
      setError(null);

      try {
        const requestParams: IAgentRecommendRequest = {
          page: params?.page || 1,
          page_size: params?.page_size || 20,
          sort: params?.sort || 'score_based_random',
          ...(params?.sort_seed ? { sort_seed: params.sort_seed } : {}),
        };

        const result = await getRecommendAgents(requestParams);

        if (result.code === 200 && result.data) {
          const data: IAgentRecommendData = result.data;

          // 直接替换列表（首页只调用一次，不需要追加逻辑）
          setRecommendList(data.list);

          // 更新分页信息
          setPagination({
            total: data.total,
            page: data.page,
            pageSize: data.page_size,
            totalPages: data.total_pages,
          });

          return data;
        }

        setError(result.message || '加载推荐角色失败');
        return null;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : '加载推荐角色失败';
        setError(errorMsg);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [], // 空依赖数组，保持函数引用稳定
  );

  /**
   * 刷新推荐列表
   * 重新加载第一页
   */
  const refreshRecommendList = useCallback(async () => {
    return await loadRecommendAgents({ page: 1 });
  }, [loadRecommendAgents]);

  /**
   * 加载更多推荐角色
   * 加载下一页
   */
  const loadMoreRecommendAgents = useCallback(async () => {
    if (pagination.page >= pagination.totalPages) {
      return null;
    }
    return await loadRecommendAgents({ page: pagination.page + 1 });
  }, [loadRecommendAgents, pagination.page, pagination.totalPages]);

  /**
   * 加载 Agent 详情
   * @param agentId Agent ID
   * @returns Agent 详情
   */
  const loadAgentDetail = useCallback(async (agentId: string) => {
    setDetailLoading(true);
    setError(null);

    try {
      const agentData = await getAgentDetail(agentId);

      if (agentData) {
        setCurrentAgent(agentData);
        return agentData;
      }

      setError('未找到 Agent 信息');
      return null;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '加载 Agent 详情失败';
      setError(errorMsg);
      console.error('加载 Agent 详情失败:', err);
      return null;
    } finally {
      setDetailLoading(false);
    }
  }, []);

  /**
   * 设置当前选中的角色
   * @param agent 角色信息
   */
  const selectAgent = useCallback((agent: IAgent | null) => {
    setCurrentAgent(agent);
  }, []);

  /**
   * 根据 ID 查找角色
   * @param agentId 角色 ID
   * @returns 角色信息
   */
  const findAgentById = useCallback(
    (agentId: string): IAgent | undefined => {
      return recommendList.find((agent) => agent.id === agentId);
    },
    [recommendList],
  );

  /**
   * 清除错误信息
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * 重置状态
   */
  const reset = useCallback(() => {
    setRecommendList([]);
    setCurrentAgent(null);
    setLoading(false);
    setDetailLoading(false);
    setError(null);
    setPagination({
      total: 0,
      page: 1,
      pageSize: 20,
      totalPages: 0,
    });
  }, []);

  return {
    // 状态
    recommendList,
    currentAgent,
    loading,
    detailLoading,
    error,
    pagination,

    // 方法
    loadRecommendAgents,
    refreshRecommendList,
    loadMoreRecommendAgents,
    loadAgentDetail,
    selectAgent,
    findAgentById,
    clearError,
    reset,
  };
}

