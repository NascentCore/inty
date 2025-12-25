/**
 * HTTP 模块统一导出
 */

// 导出请求方法
export { default as request, get, post, put, del as delete, patch, baseURL } from './request';

// 导出类型
export * from './types/index';

// 导出 API 接口
export * from './api';
