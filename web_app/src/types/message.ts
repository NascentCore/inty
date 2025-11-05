/**
 * 消息相关类型定义
 */

/**
 * 聊天消息角色类型
 */
export type TMessageRole = 'user' | 'assistant' | 'system';

/**
 * 聊天消息元数据
 */
export interface IMessageMetaData {
  /** Agent ID */
  agentId?: string;
  /** 是否是开场白 */
  isOpening?: boolean;
  /** 其他元数据 */
  [key: string]: unknown;
}

/**
 * 聊天消息
 */
export interface IMessage {
  /** 消息 ID */
  id: number | string;
  /** 消息内容 */
  content: string;
  /** 消息角色 */
  role: TMessageRole;
  /** 发送者类型 */
  sender_type?: string;
  /** 消息类型 */
  type?: string;
  /** 时间戳 */
  timestamp: string;
  /** 创建时间 */
  created_at?: string;
  /** 音频 URL */
  audio_url?: string | null;
  /** 元数据 */
  meta_data?: IMessageMetaData | null;
}

/**
 * 获取聊天消息请求参数
 */
export interface IGetChatMessagesRequest {
  /** Agent ID */
  agent_id: string;
  /** 每页消息数量 */
  limit?: number;
  /** 偏移量 */
  offset?: number;
  /** 排序方式 */
  order?: 'asc' | 'desc';
}

/**
 * 获取聊天消息响应数据
 */
export interface IGetChatMessagesResponse {
  /** 是否有更多消息 */
  has_more: boolean;
  /** 每页数量 */
  limit: number;
  /** 偏移量 */
  offset: number;
  /** 当前页码 */
  page: number;
  /** 总消息数 */
  total: number;
  /** 消息列表 */
  messages: IMessage[];
}
