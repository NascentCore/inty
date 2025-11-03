/**
 * 认证相关 API 服务
 * 使用 Inty SDK 实现
 */

import { STORAGE_KEYS } from '@/constants';
import { storage, createIntyClient, logger } from '@/utils';
import { saveToken } from '@/utils/token';
import type {
  IApiResult,
  IGuestLoginData,
  IGuestLoginRequest,
} from '@/types';

/**
 * 访客登录
 * 使用 Inty SDK 实现
 * @param params 访客登录参数
 * @returns 访客登录结果
 */
export async function guestLogin(
  params: IGuestLoginRequest,
): Promise<IApiResult<IGuestLoginData>> {
  try {
    // 创建 Inty 客户端（无需认证）
    const client = await createIntyClient();
    
    // 调用 SDK 的游客登录接口
    const response = await client.api.v1.auth.createGuest({
      device_id: params.device_id,
      system_language: params.system_language,
      age_group: params.age_group,
      request_id: params.request_id,
    });
    logger.info("访客登录响应", response);

    // 转换为项目的统一格式
    const guestData: IGuestLoginData = {
      token: response.data?.token || '',
      guest_id: response.data?.guest_id || '',
      is_new_guest: response.data?.is_new_guest || false,
    };

    const result: IApiResult<IGuestLoginData> = {
      code: response.code || 200,
      message: response.message || 'success',
      data: guestData,
    };

    // 登录成功后自动保存 token 到 IndexedDB
    if (result.code === 200 && result.data) {
      await Promise.all([
        saveToken(result.data.token),
        storage.set('guest_login_data', result.data),
      ]);
    }

    return result;
  } catch (err: unknown) {
    logger.error('访客登录失败', err);
    
    // 返回错误结果（使用空数据而非 null）
    const error = err as { status?: number; message?: string };
    return {
      code: error.status || 500,
      message: error.message || '访客登录失败',
      data: {
        token: '',
        guest_id: '',
        is_new_guest: false,
      },
    };
  }
}

/**
 * 获取访客登录信息
 * @returns 访客登录数据，如果未登录则返回 null
 */
export async function getGuestInfo(): Promise<IGuestLoginData | null> {
  return await storage.get<IGuestLoginData>('guest_login_data');
}

/**
 * 清除访客登录信息
 * @returns 是否清除成功
 */
export async function clearGuestInfo(): Promise<boolean> {
  return await storage.remove('guest_login_data');
}

