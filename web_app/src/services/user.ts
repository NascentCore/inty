/**
 * 用户相关 API 服务
 * 封装用户信息获取、更新等接口
 */

import type { IUserProfile } from '@/types';
import { createIntyClient, logger } from '@/utils';

/**
 * 获取当前用户信息
 * 调用 SDK API: client.api.v1.users.profile.me()
 * @returns 用户信息，如果失败返回 null
 */
export async function getUserProfile(): Promise<IUserProfile | null> {
  try {
    logger.info('开始获取用户信息');

    const client = await createIntyClient(true);
    const response = await client.api.v1.users.profile.me();
    logger.info('获取用户信息响应', response);

    if (response.code === 200 && response.data) {
      return response.data as IUserProfile;
    }
    return null;
  } catch (err: unknown) {
    logger.error('获取用户信息异常', err);
    return null;
  }
}

/**
 * 更新用户资料
 * 调用 SDK API: client.api.v1.users.profile.update()
 * @param updates 要更新的用户信息
 * @returns 更新后的用户信息，如果失败返回 null
 */
export async function updateUserProfile(
  updates: Partial<IUserProfile>,
): Promise<IUserProfile | null> {
  try {
    logger.info('开始更新用户资料', updates);

    const client = await createIntyClient(true);
    const response = await client.api.v1.users.profile.update(updates);
    logger.info('更新用户资料响应', response);

    if (response.code === 200 && response.data) {
      return response.data as IUserProfile;
    }

    logger.warn('更新用户资料失败', response.message);
    return null;
  } catch (err: unknown) {
    logger.error('更新用户资料异常', err);
    return null;
  }
}
