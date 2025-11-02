/**
 * 用户相关 API 服务
 * 封装用户信息获取、更新等接口
 */

import { createIntyClient, logger } from '@/utils';
import type { IUserProfile } from '@/types';

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

    if (response.code === 200 && response.data) {
      logger.info('获取用户信息成功', response.data);
      return response.data as IUserProfile;
    }

    logger.warn('获取用户信息失败', response.message);
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

    if (response.code === 200 && response.data) {
      logger.info('更新用户资料成功', response.data);
      return response.data as IUserProfile;
    }

    logger.warn('更新用户资料失败', response.message);
    return null;
  } catch (err: unknown) {
    logger.error('更新用户资料异常', err);
    return null;
  }
}

