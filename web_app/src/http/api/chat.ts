/**
 * 聊天相关 API
 */

import request from '../request';
import type { ApiResult } from '../types/index';
import type {
  GetChatListParams,
  SendMessageRequest,
  SendMessageResponse,
  GetChatMessagesParams,
  GetChatMessagesResponse,
  GenerateVoiceResponse,
  ClearMessagesRequest,
  ClearMessagesResponse,
} from '../types/chat';

/**
 * 获取聊天列表
 */
export function getChatList(params: GetChatListParams): Promise<any[]> {
  return request.get('/api/v1/chats/', { params });
}

/**
 * 发送消息
 */
export function sendMessage(agentId: string, data: SendMessageRequest): Promise<ApiResult<SendMessageResponse>> {
  return request.post(`/api/v1/chats/${agentId}/completion`, data);
}

/**
 * 获取聊天消息
 */
export function getChatMessages(agentId: string, params: GetChatMessagesParams): Promise<GetChatMessagesResponse> {
  return request.get(`/api/v1/chats/agents/${agentId}/messages`, { params });
}

/**
 * 生成消息语音
 */
export function generateMessageVoice(messageId: string, params: { agent_id: string }): Promise<ApiResult<GenerateVoiceResponse>> {
  return request.post(`/api/v1/chats/agents/voices/${messageId}`, params);
}

/**
 * 删除聊天消息
 */
export function clearMessages(agentId: string, data: ClearMessagesRequest): Promise<ClearMessagesResponse> {
  return request.post(`/api/v1/chats/agents/${agentId}/clear-messages`, data);
}
