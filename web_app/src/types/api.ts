/**
 * API 通用类型定义
 */

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
 * 访客登录请求参数
 */
export interface IGuestLoginRequest {
  /** 设备 ID（可选） */
  device_id?: string;
  /** 系统语言（可选） */
  system_language?: string;
  /** 年龄组（可选） */
  age_group?: string;
  /** 请求 ID（可选） */
  request_id?: string;
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
