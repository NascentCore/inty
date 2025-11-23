/**
 * 项目常量配置
 */

// 应用信息
export const APP_NAME = 'My Chat App';
export const APP_VERSION = '1.0.0';

// 布局相关
export const LAYOUT_HEADER_HEIGHT = 64;
export const LAYOUT_MAX_WIDTH = 1400;
export const LAYOUT_PADDING = 24;

// 主题颜色
export const THEME_COLORS = {
  primary: '#1890ff',
  success: '#52c41a',
  warning: '#faad14',
  error: '#f5222d',
  info: '#1890ff',
  background: '#f0f2f5',
  white: '#ffffff',
  textPrimary: 'rgba(0, 0, 0, 0.85)',
  textSecondary: 'rgba(0, 0, 0, 0.65)',
  border: '#f0f0f0',
  hover: '#f5f5f5',
  activeBackground: '#e6f7ff',
} as const;

// 响应式断点
export const BREAKPOINTS = {
  xs: 480,
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
  xxl: 1600,
} as const;

// 本地存储键名
export const STORAGE_KEYS = {
  /** 用户信息 */
  USER_INFO: 'user_info',
  /** 统一 Token（访客和正式用户共用） */
  TOKEN: 'token',
  /** 设备 ID */
  DEVICE_ID: 'device_id',
  /** 语言设置 */
  LANGUAGE: 'language',
  /** 主题设置 */
  THEME: 'theme',
} as const;

// IndexedDB 配置
export const STORAGE_CONFIG = {
  /** 数据库名称 */
  DB_NAME: 'intellimate_db',
  /** 存储仓库名称 */
  STORE_NAME: 'intellimate_store',
  /** 数据库版本 */
  VERSION: 1.0,
  /** 数据库描述 */
  DESCRIPTION: 'IntelliMate 本地数据存储',
} as const;

// 国际化语言选项
export const LOCALES = {
  ZH_CN: 'zh-CN',
  EN_US: 'en-US',
} as const;

// Inty SDK 配置
export const INTY_SDK_CONFIG = {
  /** Base URL - 统一使用相对路径，通过代理转发 */
  BASE_URL: `${window.location.origin}/`,
  /** 默认超时时间 (毫秒) */
  TIMEOUT: 30000,
  /** 默认重试次数 */
  MAX_RETRIES: 0,
  /** 日志级别 */
  LOG_LEVEL: 'warn' as const,
} as const;

// Google OAuth 配置
export const GOOGLE_AUTH_CONFIG = {
  /** Google OAuth Client ID */
  CLIENT_ID: '1034291688895-0e5hq72pghd4nihhpmf989ptv0ag1542.apps.googleusercontent.com',
} as const;

// 默认 Agent 头像（SVG Data URI，CREATED_BY_AGENT）
export const DEFAULT_AGENT_AVATAR =
  'data:image/svg+xml;utf8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2064%2064%22%3E%0A%20%20%3Cdefs%3E%0A%20%20%20%20%3ClinearGradient%20id%3D%22g%22%20x1%3D%220%22%20y1%3D%220%22%20x2%3D%221%22%20y2%3D%221%22%3E%0A%20%20%20%20%20%20%3Cstop%20offset%3D%220%25%22%20stop-color%3D%22%23667eea%22%2F%3E%0A%20%20%20%20%20%20%3Cstop%20offset%3D%22100%25%22%20stop-color%3D%22%23764ba2%22%2F%3E%0A%20%20%20%20%3C%2FlinearGradient%3E%0A%20%20%3C%2Fdefs%3E%0A%20%20%3Ccircle%20cx%3D%2232%22%20cy%3D%2232%22%20r%3D%2232%22%20fill%3D%22url%28%23g%29%22%2F%3E%0A%20%20%3Ccircle%20cx%3D%2232%22%20cy%3D%2226%22%20r%3D%2211%22%20fill%3D%22white%22%20fill-opacity%3D%220.9%22%2F%3E%0A%20%20%3Cpath%20d%3D%22M16%2051c4.5-8%2012-12%2016-12s11.5%204%2016%2012%22%20stroke%3D%22white%22%20stroke-opacity%3D%220.8%22%20stroke-width%3D%224%22%20stroke-linecap%3D%22round%22%2F%3E%0A%3C%2Fsvg%3E%3C%21--CREATED_BY_AGENT--%3E';
