/**
 * 项目类型定义
 * 注意：接口名称统一以大写字母 "I" 开头
 */

// 导出聊天相关类型
export * from './chat';

/**
 * 菜单项接口
 */
export interface IMenuItem {
  /** 路由路径 */
  path: string;
  /** 菜单显示标签 */
  label: string;
  /** 菜单图标（可以是 emoji 或图标组件） */
  icon?: string | React.ReactNode;
  /** 是否在菜单中隐藏 */
  hideInMenu?: boolean;
  /** 子菜单项 */
  children?: IMenuItem[];
}

/**
 * 用户信息接口（简化版）
 */
export interface IUserInfo {
  /** 用户 ID */
  id: string;
  /** 用户名 */
  username: string;
  /** 昵称 */
  nickname?: string;
  /** 头像 URL */
  avatar?: string;
  /** 邮箱 */
  email?: string;
  /** 手机号 */
  phone?: string;
}

/**
 * 用户性别枚举
 */
export type TUserGender = 'MALE' | 'FEMALE' | 'OTHER';

/**
 * 用户认证类型
 */
export type TUserAuthType = 'PHONE' | 'GOOGLE' | 'GUEST';

/**
 * 用户详细信息接口（来自 SDK API）
 */
export interface IUserProfile {
  /** 用户 ID */
  id: string;
  /** 认证类型 */
  auth_type: TUserAuthType;
  /** 创建时间 */
  created_at: string;
  /** 是否激活 */
  is_active: boolean;
  /** 可读 ID */
  readable_id: string;
  /** 年龄组 */
  age_group?: string | null;
  /** 头像 URL */
  avatar?: string | null;
  /** 连接数 */
  connector_count?: number | null;
  /** 个人简介 */
  description?: string | null;
  /** 邮箱 */
  email?: string | null;
  /** 关注者数量 */
  followers_count?: number | null;
  /** 性别 */
  gender?: TUserGender | null;
  /** 是否超级用户 */
  is_superuser?: boolean;
  /** 昵称 */
  nickname?: string | null;
  /** 手机号 */
  phone?: string | null;
  /** 公开 Agent 数量 */
  public_agents_count?: number | null;
  /** 系统语言 */
  system_language?: string | null;
  /** 公开 Agent 关注总数 */
  total_public_agents_follows?: number | null;
  /** 更新时间 */
  updated_at?: string | null;
}

/**
 * 应用初始状态接口
 */
export interface IInitialState {
  /** 应用名称 */
  name?: string;
}

/**
 * 路由配置接口
 */
export interface IRouteConfig {
  /** 路由路径 */
  path: string;
  /** 组件路径 */
  component?: string;
  /** 路由名称 */
  name?: string;
  /** 图标 */
  icon?: string;
  /** 子路由 */
  routes?: IRouteConfig[];
  /** 重定向 */
  redirect?: string;
  /** 布局包装器 */
  wrappers?: string[];
  /** 是否隐藏子菜单 */
  hideChildrenInMenu?: boolean;
  /** 是否在菜单中隐藏 */
  hideInMenu?: boolean;
}

/**
 * API 响应基础结构
 */
export interface IApiResponse<T = any> {
  /** 是否成功 */
  success: boolean;
  /** 响应数据 */
  data: T;
  /** 错误代码 */
  errorCode?: string;
  /** 错误信息 */
  errorMessage?: string;
  /** 显示类型 */
  showType?: number;
}

/**
 * 分页参数接口
 */
export interface IPaginationParams {
  /** 当前页码 */
  current: number;
  /** 每页条数 */
  pageSize: number;
}

/**
 * 分页响应接口
 */
export interface IPaginationResponse<T = any> {
  /** 数据列表 */
  list: T[];
  /** 总数 */
  total: number;
  /** 当前页码 */
  current: number;
  /** 每页条数 */
  pageSize: number;
}

/**
 * 主题配置接口
 */
export interface IThemeConfig {
  /** 主题模式 */
  mode: 'light' | 'dark';
  /** 主色调 */
  primaryColor?: string;
  /** 字体家族 */
  fontFamily?: string;
}

/**
 * 布局配置接口
 */
export interface ILayoutConfig {
  /** 布局类型 */
  layout?: 'side' | 'top' | 'mix';
  /** 导航主题 */
  navTheme?: 'light' | 'dark';
  /** 固定头部 */
  fixedHeader?: boolean;
  /** 固定侧边栏 */
  fixSiderbar?: boolean;
}

/**
 * 通用 API 响应结构（与后端约定）
 */
export interface IApiResult<T = unknown> {
  /** 响应状态码 */
  code: number;
  /** 响应消息 */
  message: string;
  /** 响应数据 */
  data: T;
}

/**
 * 访客登录请求参数
 */
export interface IGuestLoginRequest {
  /** 设备 ID */
  device_id: string;
  /** 系统语言 */
  system_language: string;
  /** 年龄组 */
  age_group: string;
  /** 请求 ID */
  request_id: string;
}

/**
 * 访客登录响应数据
 */
export interface IGuestLoginData {
  /** 访客 ID */
  guest_id: string;
  /** 访问令牌 */
  token: string;
  /** 是否为新访客 */
  is_new_guest: boolean;
}

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

