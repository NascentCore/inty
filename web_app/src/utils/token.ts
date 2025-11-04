/**
 * Token 管理工具
 * 统一管理用户 Token 的存储与获取（包括访客和正式用户）
 */

import { storage } from './storage';
import { STORAGE_KEYS } from '@/constants';
import { logger } from './logger';

/**
 * 获取 Token
 * @returns Token 字符串，如果未登录则返回空字符串
 */
export async function getToken(): Promise<string | null> {
  try {
    const token = await storage.get<string>(STORAGE_KEYS.TOKEN);
    return token || '';
  } catch (err) {
    logger.error('获取 Token 失败', err);
    return '';
  }
}

/**
 * 保存 Token 到本地存储
 * @param token - API Token（访客或正式用户）
 */
export async function saveToken(token: string): Promise<void> {
  try {
    await storage.set(STORAGE_KEYS.TOKEN, token);
    logger.info('Token 已保存到本地存储');
  } catch (err) {
    logger.error('保存 Token 失败', err);
  }
}

/**
 * 清除本地存储的 Token
 */
export async function clearToken(): Promise<void> {
  try {
    await storage.remove(STORAGE_KEYS.TOKEN);
    logger.info('Token 已从本地存储清除');
  } catch (err) {
    logger.error('清除 Token 失败', err);
  }
}

/**
 * 检查是否存在有效的 Token
 * @returns 是否存在 Token
 */
export async function hasToken(): Promise<boolean> {
  try {
    const token = await getToken();
    return !!token && token.length > 0;
  } catch (err) {
    logger.error('检查 Token 存在性失败', err);
    return false;
  }
}

/**
 * 【临时测试方法】设置默认测试 Token
 * ⚠️ 仅用于开发测试，项目开发完成后需要删除
 * 
 * 用途：在应用启动时自动设置一个默认 token，避免每次测试都需要手动登录
 * 
 * @param testToken - 测试用的 token 字符串（可选，默认使用预设值）
 */
export async function setDefaultTestToken(
  testToken?: string,
): Promise<void> {
  try {
    // 检查是否已存在 token
    const existingToken = await hasToken();
    if (existingToken) {
      logger.info('已存在 Token，跳过设置默认测试 Token');
      return;
    }

    // 使用提供的 token 或默认测试 token
    const defaultToken =
      testToken ||
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODQzNjAyMjAsInN1YiI6InVzZXItMDFKV1ozNFk0RDFDOTJHRDg2QTVSNkVXWUoifQ.vsYKRvrCfxWgJ5wkTjAYby3RrIOm6P-9VbcCg4msjlM'; // TODO: 替换为实际的测试 token

    await saveToken(defaultToken);
    logger.warn(
      '⚠️ 已设置默认测试 Token（仅用于开发测试）',
      defaultToken.substring(0, 20) + '...',
    );
  } catch (err) {
    logger.error('设置默认测试 Token 失败', err);
  }
}

