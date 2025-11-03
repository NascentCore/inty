/**
 * 认证相关 API 服务
 * 使用 Inty SDK 实现
 * 
 * ⚠️ 注意：以下访客登录相关函数仅供 dev-test 页面测试使用
 * 业务代码中不再使用访客登录逻辑
 */

import { STORAGE_KEYS } from '@/constants';
import { storage, createIntyClient, logger } from '@/utils';
import { saveToken, getGuestToken } from '@/utils/token';
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

    // 登录成功后自动保存 token 和 guest_id 到 IndexedDB
    if (result.code === 200 && result.data) {
      await Promise.all([
        saveToken(result.data.token), // 保存到 TOKEN key
        storage.setMultiple({
          [STORAGE_KEYS.GUEST_TOKEN]: result.data.token,
          [STORAGE_KEYS.GUEST_ID]: result.data.guest_id,
          guest_login_data: result.data,
        }),
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
 * 获取访客 Token（从 utils/token.ts 重新导出）
 * @deprecated 请直接从 @/utils/token 导入
 * @returns 访客 Token，如果未登录则返回 null
 */
export { getGuestToken };

/**
 * 清除访客登录信息
 * @returns 是否清除成功
 */
export async function clearGuestInfo(): Promise<boolean> {
  return await storage.removeMultiple([
    STORAGE_KEYS.GUEST_TOKEN,
    STORAGE_KEYS.GUEST_ID,
    'guest_login_data',
  ]);
}

