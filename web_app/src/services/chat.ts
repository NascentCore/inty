/**
 * 聊天相关 API 服务
 * 使用 Inty SDK 实现
 */

import { createIntyClient, logger } from '@/utils';
import type { IGetChatMessagesRequest, IGetChatMessagesResponse } from '@/types';

/**
 * 发送消息响应接口
 */
export interface ISendMessageResponse {
  /** AI 回复内容 */
  content: string;
  /** 消息 ID */
  messageId: number;
  /** 音频 URL（如果有） */
  audioUrl?: string | null;
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
    logger.info('获取聊天消息响应', response);

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
 * 消息发送错误类型
 */
export class MessageSendError extends Error {
  constructor(
    message: string,
    public errorCode?: string,
    public shouldLogin?: boolean,
  ) {
    super(message);
    this.name = 'MessageSendError';
  }
}

/**
 * 发送消息（使用 V1 API）
 * @param agentId Agent ID
 * @param content 消息内容
 * @returns AI 回复
 */
export async function sendMessage(agentId: string, content: string): Promise<ISendMessageResponse> {
  try {
    // 获取已认证的客户端
    const client = await createIntyClient(true);

    logger.info('发送消息', { agentId, content });

    // 调用 V1 API 发送消息
    const response = await client.api.v1.chats.createCompletion(agentId, {
      messages: [{ role: 'user', content }],
      stream: false,
    });
    logger.info('发送消息响应', response);

    const responseData = response as any;

    // 检查响应状态码
    if (responseData.code === 200) {
      // 成功响应，提取 AI 回复内容
      const message = responseData.data?.choices?.[0]?.message;

      if (!message?.content) {
        throw new MessageSendError('Invalid response: missing message content');
      }

      return {
        content: message.content,
        messageId: message.id,
        audioUrl: message.audio_url,
      };
    }

    // 错误响应
    const errorCode = responseData.data?.error_code;
    const errorMessage = responseData.message || 'Message send failed';

    // GUEST_LOGIN_REQUIRED 错误，需要触发登录
    if (errorCode === 'GUEST_LOGIN_REQUIRED') {
      throw new MessageSendError(errorMessage, errorCode, true);
    }

    // 其他错误
    throw new MessageSendError(errorMessage, errorCode, false);
  } catch (err: unknown) {
    // 如果已经是 MessageSendError，直接抛出
    if (err instanceof MessageSendError) {
      throw err;
    }

    logger.error('发送消息失败', err);
    throw new MessageSendError('Failed to send message, please try again later');
  }
}

/**
 * 语音生成响应接口
 */
export interface IGenerateVoiceResponse {
  /** 音频 URL */
  audio_url: string;
  /** 消息 ID */
  message_id: string;
  /** 语音 ID */
  voice_id: string;
  /** 语言 */
  language: string;
  /** 音频时长（秒） */
  audio_duration: number;
  /** 是否命中缓存 */
  cached: boolean;
  /** 生成耗时 */
  generation_time: number | null;
}

/**
 * 语音生成错误类型
 */
export class VoiceGenerationError extends Error {
  constructor(
    message: string,
    public errorCode?: string,
    public shouldLogin?: boolean,
  ) {
    super(message);
    this.name = 'VoiceGenerationError';
  }
}

/**
 * 生成消息语音
 * @param messageId 消息 ID
 * @param agentId Agent ID
 * @returns 语音信息
 */
export async function generateMessageVoice(
  messageId: string | number,
  agentId: string,
): Promise<IGenerateVoiceResponse> {
  try {
    // 获取已认证的客户端
    const client = await createIntyClient(true);

    logger.info('生成消息语音', { messageId, agentId });

    // 调用 SDK 生成语音
    const response = await client.api.v1.chats.agents.generateMessageVoice(String(messageId), {
      agent_id: agentId,
    });

    logger.info('生成语音响应', response);

    const responseData = response as any;

    // 检查响应状态码
    if (responseData.code === 200) {
      // 成功响应，返回 data
      return responseData.data;
    }

    // 错误响应
    const errorCode = responseData.data?.error_code;
    const errorMessage = responseData.message || 'Voice generation failed';

    // GUEST_LOGIN_REQUIRED 错误，需要触发登录
    if (errorCode === 'GUEST_LOGIN_REQUIRED') {
      throw new VoiceGenerationError(errorMessage, errorCode, true);
    }

    // 其他错误
    throw new VoiceGenerationError(errorMessage, errorCode, false);
  } catch (err: unknown) {
    // 如果已经是 VoiceGenerationError，直接抛出
    if (err instanceof VoiceGenerationError) {
      throw err;
    }

    logger.error('生成消息语音失败', err);
    throw new VoiceGenerationError('Failed to generate voice, please try again later');
  }
}
