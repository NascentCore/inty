/**
 * 聊天相关 API 服务
 * 使用 Inty SDK 实现
 */

import { createIntyClient, logger } from '@/utils';
import type {
  IGetChatMessagesRequest,
  IGetChatMessagesResponse,
} from '@/types';

/**
 * 发送消息响应接口
 */
export interface ISendMessageResponse {
  /** AI 回复内容 */
  content: string;
  /** 响应原始数据 */
  data?: unknown;
}

/**
 * 获取与指定 Agent 的聊天消息历史
 * 使用 Inty SDK 实现
 * @param params 请求参数
 * @returns 聊天消息列表
 */
export async function getChatMessages(
  params: IGetChatMessagesRequest,
): Promise<IGetChatMessagesResponse> {
  try {
    // 获取已认证的客户端
    const client = await createIntyClient(true);
    
    const { agent_id, limit = 100, offset = 0, order = 'asc' } = params;

    // 调用 SDK 获取消息列表，传递分页参数
    const response = await client.api.v1.chats.agents.getMessages(agent_id, {
      limit,
      offset,
      order,
    });

    logger.info('获取聊天消息成功', response);

    // SDK 返回的是包含 messages 数组的对象
    let messages: any[] = [];
    let total = 0;
    let hasMore = false;
    
    if (response && typeof response === 'object') {
      // 如果返回的是对象且包含 messages 字段
      if ('messages' in response && Array.isArray(response.messages)) {
        messages = response.messages;
      } 
      // 如果返回的直接是数组
      else if (Array.isArray(response)) {
        messages = response;
      }
      
      // 获取服务器返回的分页信息
      if ('total' in response && typeof response.total === 'number') {
        total = response.total;
      } else {
        total = messages.length;
      }
      
      if ('has_more' in response && typeof response.has_more === 'boolean') {
        hasMore = response.has_more;
      } else {
        hasMore = false;
      }
    }
    
    const currentPage = Math.floor(offset / limit) + 1;

    return {
      has_more: hasMore,
      limit: limit,
      offset: offset,
      page: currentPage,
      total: total,
      messages: messages,
    };
  } catch (err: unknown) {
    logger.error('获取聊天消息失败', err);
    
    // 返回错误结果
    return {
      has_more: false,
      limit: params.limit || 100,
      offset: params.offset || 0,
      page: 1,
      total: 0,
      messages: [],
    };
  }
}

/**
 * 发送消息（使用 V1 API）
 * @param agentId Agent ID
 * @param content 消息内容
 * @returns AI 回复
 */
export async function sendMessage(
  agentId: string,
  content: string,
): Promise<ISendMessageResponse> {
  try {
    // 获取已认证的客户端
    const client = await createIntyClient(true);

    logger.info('发送消息', { agentId, content });

    // 调用 V1 API 发送消息
    const response = await client.api.v1.chats.createCompletion(agentId, {
      messages: [{ role: 'user', content }],
      stream: false,
    });

    logger.info('发送消息成功', response);

    // 提取 AI 回复内容
    const aiContent = extractAIResponse(response);

    return {
      content: aiContent,
      data: response.data,
    };
  } catch (err: unknown) {
    logger.error('发送消息失败', err);
    throw new Error('发送消息失败，请稍后重试');
  }
}

/**
 * 从 API 响应中提取 AI 回复内容
 * @param response API 响应
 * @returns AI 回复文本
 */
function extractAIResponse(response: any): string {
  try {
    // 尝试从不同可能的路径提取内容
    if (response?.data?.content) {
      return response.data.content;
    }
    if (response?.data?.message) {
      return response.data.message;
    }
    if (response?.data?.choices?.[0]?.message?.content) {
      return response.data.choices[0].message.content;
    }
    if (typeof response?.data === 'string') {
      return response.data;
    }
    
    // 如果找不到明确的回复内容，返回默认消息
    logger.warn('无法提取 AI 回复内容', response);
    return '收到回复，但无法解析内容';
  } catch (err) {
    logger.error('提取 AI 回复失败', err);
    return '回复解析失败';
  }
}

