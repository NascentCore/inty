/**
 * AI 角色相关类型定义
 */

/**
 * AI 角色性别枚举
 */
export type TAgentGender = 'MALE' | 'FEMALE' | 'OTHER';

/**
 * AI 角色状态枚举
 */
export type TAgentStatus = 'PENDING' | 'APPROVED' | 'REJECTED';

/**
 * AI 角色可见性枚举
 */
export type TAgentVisibility = 'PUBLIC' | 'PRIVATE';

/**
 * 用户认证类型枚举
 */
export type TAuthType = 'GOOGLE' | 'EMAIL' | 'PHONE';

/**
 * 头像裁剪配置
 */
export interface IAvatarCrop {
  /** X 坐标 */
  x: number;
  /** Y 坐标 */
  y: number;
  /** 宽度 */
  width: number;
  /** 高度 */
  height: number;
  /** 图片宽度 */
  imageWidth: number;
  /** 图片高度 */
  imageHeight: number;
}

/**
 * 图片尺寸信息
 */
export interface IImageSize {
  /** 宽度 */
  width: number;
  /** 高度 */
  height: number;
}

/**
 * AI 角色元数据
 */
export interface IAgentMetaData {
  /** 评分 */
  score?: number;
  /** 评论 */
  comment?: string | null;
}

/**
 * AI 角色创建者信息
 */
export interface IAgentCreator {
  /** 可读 ID */
  readable_id: string;
  /** 昵称 */
  nickname: string | null;
  /** 头像 */
  avatar: string | null;
  /** 邮箱 */
  email: string | null;
  /** 手机号 */
  phone: string | null;
  /** 性别 */
  gender: TAgentGender;
  /** 年龄组 */
  age_group: string | null;
  /** 描述 */
  description: string | null;
  /** 系统语言 */
  system_language: string | null;
  /** 用户 ID */
  id: string;
  /** 认证类型 */
  auth_type: TAuthType;
  /** 是否激活 */
  is_active: boolean;
  /** 创建时间 */
  created_at: string;
  /** 更新时间 */
  updated_at: string;
  /** 是否为超级用户 */
  is_superuser: boolean;
  /** 公开角色数量 */
  public_agents_count: number;
  /** 公开角色被关注总数 */
  total_public_agents_follows: number;
  /** 粉丝数量 */
  followers_count: number;
  /** 连接器数量 */
  connector_count: number;
}

/**
 * AI 角色详细信息
 */
export interface IAgent {
  /** 角色名称 */
  name: string;
  /** 性别 */
  gender: TAgentGender;
  /** 头像 URL */
  avatar: string;
  /** 背景图 URL */
  background: string;
  /** 背景图列表 */
  background_images: string[];
  /** 语音 ID */
  voice_id: string | null;
  /** 设置 */
  settings: Record<string, unknown>;
  /** 简介 */
  intro: string;
  /** 开场白 */
  opening: string;
  /** 开场白音频 URL */
  opening_audio_url: string | null;
  /** 可见性 */
  visibility: TAgentVisibility;
  /** 照片 */
  photos: string[] | null;
  /** 分类 */
  category: string | null;
  /** 提示词 */
  prompt: string | null;
  /** 主提示词 */
  main_prompt: string | null;
  /** 模式提示词 */
  mode_prompt: string | null;
  /** 角色卡片规范 */
  character_card_spec: string | null;
  /** 个性描述 */
  personality: string | null;
  /** 场景描述 */
  scenario: string | null;
  /** 消息示例 */
  message_example: string | null;
  /** 创建者备注 */
  creator_notes: string | null;
  /** 历史后指令 */
  post_history_instructions: string | null;
  /** 备用问候语 */
  alternate_greetings: string[] | null;
  /** 角色书 */
  character_book: unknown | null;
  /** 标签列表 */
  tags: string[];
  /** 角色版本 */
  character_version: string | null;
  /** 扩展信息 */
  extensions: {
    avatar_crop?: IAvatarCrop;
  } | null;
  /** LLM 配置 */
  llm_config: unknown | null;
  /** 元数据 */
  meta_data: IAgentMetaData | null;
  /** 角色 ID */
  id: string;
  /** 可读 ID */
  readable_id: string;
  /** 状态 */
  status: TAgentStatus;
  /** 创建者 ID */
  creator_id: string;
  /** 创建时间（时间戳） */
  created_at: number;
  /** 更新时间（时间戳） */
  updated_at: number;
  /** 删除时间（时间戳） */
  deleted_at: number | null;
  /** 是否已关注 */
  is_followed: boolean;
  /** 关注者数量 */
  follower_count: number;
  /** 连接器数量 */
  connector_count: number;
  /** 创建者信息 */
  creator: IAgentCreator;
  /** 头像尺寸 */
  avatar_size: IImageSize | null;
  /** 背景图尺寸 */
  background_size: IImageSize | null;
  /** 用户标识 */
  user: string;
}

/**
 * 推荐 AI 角色列表请求参数
 */
export interface IAgentRecommendRequest {
  /** 页码 */
  page: number;
  /** 每页数量 */
  page_size: number;
  /** 排序种子 */
  sort_seed?: string;
  /** 排序方式 */
  sort?: 'score_based_random' | 'created_at' | 'updated_at';
}

/**
 * 推荐 AI 角色列表响应数据
 */
export interface IAgentRecommendData {
  /** 角色列表 */
  list: IAgent[];
  /** 总数 */
  total: number;
  /** 当前页码 */
  page: number;
  /** 每页数量 */
  page_size: number;
  /** 总页数 */
  total_pages: number;
}
