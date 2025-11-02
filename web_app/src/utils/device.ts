/**
 * 设备标识管理工具
 * 用于生成和管理设备唯一 ID，主要用于访客登录
 */

import { storage } from './storage';
import { STORAGE_KEYS } from '@/constants';
import { logger } from './logger';

/**
 * 生成 UUID v4
 * @returns UUID 字符串
 */
function generateUUID(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    // 使用原生 crypto.randomUUID (现代浏览器支持)
    return crypto.randomUUID();
  }

  // 降级方案：手动生成 UUID v4
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * 生成设备 ID
 * @returns 设备 ID
 */
function generateDeviceId(): string {
  return generateUUID();
}

/**
 * 获取或生成设备 ID
 * 优先从存储中获取，如果不存在则生成新的设备 ID
 * @returns 设备 ID
 */
export async function getOrCreateDeviceId(): Promise<string> {
  try {
    // 尝试从存储中获取已有的设备 ID
    const existingDeviceId = await storage.get<string>(STORAGE_KEYS.DEVICE_ID);

    if (existingDeviceId) {
      return existingDeviceId;
    }

    // 生成新的设备 ID
    const deviceId = generateDeviceId();

    // 保存到存储
    await storage.set(STORAGE_KEYS.DEVICE_ID, deviceId);

    return deviceId;
  } catch (err) {
    logger.error('获取设备 ID 失败', err);
    // 如果存储也失败，返回临时 ID（仅在内存中有效）
    return generateDeviceId();
  }
}

/**
 * 重新生成设备 ID
 * 会覆盖已有的设备 ID
 * @returns 新的设备 ID
 */
export async function regenerateDeviceId(): Promise<string> {
  try {
    // 删除旧的设备 ID
    await storage.remove(STORAGE_KEYS.DEVICE_ID);

    // 生成新的设备 ID
    return await getOrCreateDeviceId();
  } catch (err) {
    logger.error('重新生成设备 ID 失败', err);
    return generateDeviceId();
  }
}

/**
 * 获取当前设备 ID（不会创建新的）
 * @returns 设备 ID，如果不存在则返回 null
 */
export async function getCurrentDeviceId(): Promise<string | null> {
  try {
    return await storage.get<string>(STORAGE_KEYS.DEVICE_ID);
  } catch (err) {
    logger.error('获取当前设备 ID 失败', err);
    return null;
  }
}

/**
 * 清除设备 ID
 * @returns 是否清除成功
 */
export async function clearDeviceId(): Promise<boolean> {
  try {
    return await storage.remove(STORAGE_KEYS.DEVICE_ID);
  } catch (err) {
    logger.error('清除设备 ID 失败', err);
    return false;
  }
}

