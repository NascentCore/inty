/**
 * 测试错误处理工具
 * 统一处理测试组件中的错误，提供友好的错误提示
 */

import { message } from 'antd';
// @ts-expect-error - inty SDK is installed as a file dependency
import Inty from 'inty';
import { logger } from './logger';

/**
 * 错误类型枚举
 */
export enum ErrorType {
  /** Token 未找到 */
  NO_TOKEN = 'NO_TOKEN',
  /** 认证失败 */
  AUTH_FAILED = 'AUTH_FAILED',
  /** 资源未找到 */
  NOT_FOUND = 'NOT_FOUND',
  /** 权限不足 */
  FORBIDDEN = 'FORBIDDEN',
  /** 网络错误 */
  NETWORK_ERROR = 'NETWORK_ERROR',
  /** 未知错误 */
  UNKNOWN = 'UNKNOWN',
}

/**
 * 错误信息映射
 */
const ERROR_MESSAGES: Record<ErrorType, string> = {
  [ErrorType.NO_TOKEN]: '未找到 Token，请先执行游客登录',
  [ErrorType.AUTH_FAILED]: '认证失败，请重新登录',
  [ErrorType.NOT_FOUND]: '资源不存在',
  [ErrorType.FORBIDDEN]: '权限不足',
  [ErrorType.NETWORK_ERROR]: '网络连接失败，请检查网络',
  [ErrorType.UNKNOWN]: '操作失败，请查看控制台',
};

/**
 * 判断错误类型
 */
export function getErrorType(error: unknown): ErrorType {
  if (!error) {
    return ErrorType.UNKNOWN;
  }

  // 处理普通错误对象
  if (error instanceof Error) {
    const message = error.message;

    if (message.includes('未找到 Token') || message.includes('Token')) {
      return ErrorType.NO_TOKEN;
    }

    if (message.includes('网络') || message.includes('Network')) {
      return ErrorType.NETWORK_ERROR;
    }
  }

  // 处理 Inty SDK 错误
  if (error instanceof Inty.AuthenticationError) {
    return ErrorType.AUTH_FAILED;
  }

  if (error instanceof Inty.NotFoundError) {
    return ErrorType.NOT_FOUND;
  }

  if (error instanceof Inty.PermissionDeniedError) {
    return ErrorType.FORBIDDEN;
  }

  return ErrorType.UNKNOWN;
}

/**
 * 获取错误提示消息
 */
export function getErrorMessage(error: unknown): string {
  const errorType = getErrorType(error);
  return ERROR_MESSAGES[errorType];
}

/**
 * 处理测试错误
 * 统一显示错误提示并输出日志
 */
export function handleTestError(error: unknown, testName: string): void {
  const errorMessage = getErrorMessage(error);

  // 显示错误提示
  message.error(errorMessage);

  // 输出错误日志
  logger.testError(`${testName}失败`, error);
}

/**
 * 创建测试错误处理器
 * 返回一个函数，用于在测试组件中处理错误
 */
export function createTestErrorHandler(testName: string) {
  return (error: unknown) => {
    handleTestError(error, testName);
  };
}
