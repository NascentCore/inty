/**
 * AI 角色相关 API 服务
 * 使用 Inty SDK 实现
 */

import { createIntyClient, logger } from '@/utils';
import type { IAgentRecommendData, IAgentRecommendRequest, IApiResult } from '@/types';
import type { IAgent } from '@/types';

// SDK 排序类型
type TSdkSort = 'created_asc' | 'created_desc' | 'random' | 'score_based_random' | undefined;

/**
 * 获取 AI 角色详情
 * 使用 Inty SDK 实现
 * @param agentId Agent ID
 * @returns AI 角色详情
 */
export async function getAgentDetail(agentId: string): Promise<IAgent | null> {
  try {
    // 获取已认证的客户端
    const client = await createIntyClient(true);

    // 调用 SDK 的获取 Agent 详情接口
    const response = await client.api.v1.ai.agents.retrieve(agentId);
    logger.info('获取 Agent 详情响应', response);

    return response as IAgent;
  } catch (err: unknown) {
    logger.error('获取 Agent 详情失败', err);
    return null;
  }
}

/**
 * 获取推荐 AI 角色列表
 * 使用 Inty SDK 实现
 * @param params 请求参数
 * @returns 推荐角色列表
 */
export async function getRecommendAgents(
  params: IAgentRecommendRequest,
): Promise<IApiResult<IAgentRecommendData>> {
  try {
    // 获取已认证的客户端
    const client = await createIntyClient(true);

    // 映射排序参数：项目 sort 类型 → SDK sort 类型
    let sdkSort: TSdkSort;
    if (params.sort === 'created_at') {
      sdkSort = 'created_desc'; // 默认降序
    } else if (params.sort === 'updated_at') {
      sdkSort = 'created_desc'; // 映射为创建时间降序
    } else if (params.sort === 'score_based_random') {
      sdkSort = 'score_based_random';
    }

    // 调用 SDK 的推荐角色接口
    const response = await client.api.v1.ai.agents.recommend({
      page: params.page,
      page_size: params.page_size,
      ...(params.sort_seed ? { sort_seed: params.sort_seed } : {}),
      ...(sdkSort ? { sort: sdkSort } : {}),
    });
    logger.info('获取推荐角色响应', response);

    // 转换为项目的统一格式
    const result: IApiResult<IAgentRecommendData> = {
      code: response.code || 200,
      message: response.message || 'success',
      data: {
        list: (response.data?.list || []) as IAgent[],
        total: response.data?.total || 0,
        page: response.data?.page || params.page,
        page_size: response.data?.page_size || params.page_size,
        total_pages: Math.ceil(
          (response.data?.total || 0) / (response.data?.page_size || params.page_size),
        ),
      },
    };

    return result;
  } catch (err: unknown) {
    logger.error('获取推荐角色失败', err);

    // 返回错误结果
    const error = err as { status?: number; message?: string };
    return {
      code: error.status || 500,
      message: error.message || '获取推荐角色失败',
      data: {
        list: [],
        total: 0,
        page: params.page,
        page_size: params.page_size,
        total_pages: 0,
      },
    };
  }
}
