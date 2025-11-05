/**
 * Inty SDK 客户端统一配置工具
 * 提供统一的客户端实例创建和管理
 */

// @ts-expect-error - inty SDK is installed as a file dependency
import Inty from 'inty';
import { INTY_SDK_CONFIG } from '@/constants';
import { getToken } from './token';

/**
 * 获取当前环境的 Base URL
 * 统一使用相对路径 '/'，通过代理配置转发到实际服务器
 * - 开发环境: 通过 proxy.ts 转发到 https://dev.inty.sxwl.ai
 * - 生产环境: 直接请求到生产服务器
 */
function getBaseURL(): string {
  return INTY_SDK_CONFIG.BASE_URL;
}

/**
 * 创建 Inty SDK 客户端实例
 * @param requireAuth - 是否必须有 token（默认 false）
 * @returns Inty 客户端实例
 * @throws 当 requireAuth 为 true 但没有 token 时抛出错误
 *
 * @example
 * // 无需认证（如访客登录）
 * const client = await createIntyClient();
 *
 * // 需要认证（如获取用户信息）
 * const client = await createIntyClient(true);
 */
export async function createIntyClient(requireAuth = false): Promise<Inty> {
  const token = await getToken();

  // 如果必须要 token 但没有，抛出错误
  if (requireAuth && !token) {
    throw new Error('未找到 Token，请先登录');
  }

  return new Inty({
    apiKey: token || '',
    baseURL: getBaseURL(),
    timeout: INTY_SDK_CONFIG.TIMEOUT,
    maxRetries: INTY_SDK_CONFIG.MAX_RETRIES,
    logLevel: INTY_SDK_CONFIG.LOG_LEVEL,
  });
}
