/**
 * 聊天相关类型
 */

/**
 * 获取聊天列表参数
 */
export interface GetChatListParams {
  skip?: number;
  limit?: number;
}

/**
 * 发送消息请求参数
 */
export interface SendMessageRequest {
  messages: Array<{ role: string; content: string }>;
  stream?: boolean;
}

/**
 * 发送消息响应数据
 */
export interface SendMessageResponse {
  choices: Array<{
    message: {
      id: number;
      content: string;
      audio_url?: string;
    };
  }>;
}

/**
 * 获取聊天消息参数
 */
export interface GetChatMessagesParams {
  limit?: number;
  offset?: number;
  order?: 'asc' | 'desc';
}

/**
 * 获取聊天消息响应数据
 */
export interface GetChatMessagesResponse {
  messages: any[];
  total: number;
  has_more: boolean;
}

/**
 * 生成语音响应数据
 */
export interface GenerateVoiceResponse {
  audio_url: string;
  message_id: string;
  voice_id: string;
  language: string;
  audio_duration: number;
  cached: boolean;
  generation_time: number | null;
}

/**
 * 删除聊天消息请求参数
 */
export interface ClearMessagesRequest {
  message_id: number;
}

/**
 * 删除聊天消息响应数据
 */
export interface ClearMessagesResponse {
  success: boolean;
  message: string;
  deleted_count: number;
  target_message: {
    id: number;
    content: string;
    role: string;
    timestamp: string;
  };
  deleted_time_range: {
    from: string;
    to: string;
  };
  cutoff_timestamp: string | null;
}
