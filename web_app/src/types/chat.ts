/**
 * 聊天相关类型定义
 */

/**
 * 聊天设置
 */
export interface IChatSettings {
  language: string;
  voice_enabled: boolean;
  style_prompt: string | null;
  premium_mode: boolean;
  id: string;
  user_id: string;
  agent_id: string;
  chat_id: string;
  created_at: string;
  updated_at: string | null;
}

/**
 * 聊天会话信息（SDK 返回格式）
 */
export interface IChatItem {
  /** 聊天 ID */
  id: string;
  /** 用户 ID */
  user_id: string;
  /** Agent ID */
  agent_id: string;
  /** 创建时间 */
  created_at: string;
  /** 更新时间 */
  updated_at: string | null;
  /** 最后一条消息 */
  last_message: string;
  /** 最后消息时间 */
  last_message_time: string;
  /** Agent 名称 */
  agent_name: string;
  /** Agent 头像 */
  agent_avatar: string | null;
  /** Agent 背景图 */
  agent_background: string | null;
  /** Agent 是否已删除 */
  agent_is_deleted: boolean;
  /** Agent 简介 */
  agent_intro: string | null;
  /** Agent 开场白 */
  agent_opening: string | null;
  /** Agent 开场白音频 URL */
  agent_opening_audio_url: string | null;
  /** 聊天设置 */
  settings: IChatSettings;
}

/**
 * 聊天列表响应数据
 */
export interface IChatListData {
  /** 聊天列表 */
  data: IChatItem[];
  /** 总数 */
  total: number;
  /** 当前页码 */
  page: number;
  /** 每页数量 */
  page_size: number;
}

/**
 * 聊天列表请求参数
 */
export interface IChatListRequest {
  /** 页码 */
  page?: number;
  /** 每页数量 */
  page_size?: number;
}
