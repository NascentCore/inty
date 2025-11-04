/**
 * IndexedDB 存储工具
 * 基于 localForage 封装，提供类型安全的本地存储能力
 */

import localforage from 'localforage';
import { STORAGE_CONFIG } from '@/constants';
import { logger } from './logger';

/**
 * 初始化 localForage 配置
 * 使用 IndexedDB 作为首选存储方式
 */
localforage.config({
  driver: [
    localforage.INDEXEDDB, // 首选 IndexedDB
    localforage.WEBSQL, // 备选 WebSQL
    localforage.LOCALSTORAGE, // 最后备选 localStorage
  ],
  name: STORAGE_CONFIG.DB_NAME,
  version: STORAGE_CONFIG.VERSION,
  storeName: STORAGE_CONFIG.STORE_NAME,
  description: STORAGE_CONFIG.DESCRIPTION,
});

/**
 * 获取存储的数据
 * @param key 存储键名
 * @returns 存储的数据，如果不存在则返回 null
 */
export async function get<T = unknown>(key: string): Promise<T | null> {
  try {
    const value = await localforage.getItem<T>(key);
    return value;
  } catch (error) {
    logger.error(`[Storage] 获取数据失败 - key: ${key}`, error);
    return null;
  }
}

/**
 * 设置存储数据
 * @param key 存储键名
 * @param value 要存储的数据
 * @returns 是否存储成功
 */
export async function set<T = unknown>(key: string, value: T): Promise<boolean> {
  try {
    await localforage.setItem(key, value);
    return true;
  } catch (error) {
    logger.error(`[Storage] 设置数据失败 - key: ${key}`, error);
    return false;
  }
}

/**
 * 移除存储的数据
 * @param key 存储键名
 * @returns 是否移除成功
 */
export async function remove(key: string): Promise<boolean> {
  try {
    await localforage.removeItem(key);
    return true;
  } catch (error) {
    logger.error(`[Storage] 移除数据失败 - key: ${key}`, error);
    return false;
  }
}

/**
 * 清空所有存储数据
 * @returns 是否清空成功
 */
export async function clear(): Promise<boolean> {
  try {
    await localforage.clear();
    return true;
  } catch (error) {
    logger.error('[Storage] 清空数据失败', error);
    return false;
  }
}

/**
 * 获取所有存储的键名
 * @returns 所有键名数组
 */
export async function keys(): Promise<string[]> {
  try {
    const keyList = await localforage.keys();
    return keyList;
  } catch (error) {
    logger.error('[Storage] 获取键名列表失败', error);
    return [];
  }
}

/**
 * 获取存储的数据条数
 * @returns 数据条数
 */
export async function length(): Promise<number> {
  try {
    const len = await localforage.length();
    return len;
  } catch (error) {
    logger.error('[Storage] 获取数据条数失败', error);
    return 0;
  }
}

/**
 * 遍历所有存储的数据
 * @param iteratee 迭代器函数
 */
export async function iterate<T = unknown>(
  iteratee: (value: T, key: string, iterationNumber: number) => void,
): Promise<void> {
  try {
    await localforage.iterate<T, void>(iteratee);
  } catch (error) {
    logger.error('[Storage] 遍历数据失败', error);
  }
}

/**
 * 检查某个键是否存在
 * @param key 存储键名
 * @returns 是否存在
 */
export async function has(key: string): Promise<boolean> {
  try {
    const value = await localforage.getItem(key);
    return value !== null;
  } catch (error) {
    logger.error(`[Storage] 检查键是否存在失败 - key: ${key}`, error);
    return false;
  }
}

/**
 * 获取当前使用的存储驱动名称
 * @returns 驱动名称 (INDEXEDDB | WEBSQL | LOCALSTORAGE)
 */
export function driver(): string {
  return localforage.driver();
}

/**
 * 批量设置数据
 * @param items 要设置的数据对象
 * @returns 是否全部设置成功
 */
export async function setMultiple(items: Record<string, unknown>): Promise<boolean> {
  try {
    const promises = Object.entries(items).map(([key, value]) => localforage.setItem(key, value));
    await Promise.all(promises);
    return true;
  } catch (error) {
    logger.error('[Storage] 批量设置数据失败', error);
    return false;
  }
}

/**
 * 批量获取数据
 * @param keyList 要获取的键名数组
 * @returns 数据对象
 */
export async function getMultiple<T = unknown>(
  keyList: string[],
): Promise<Record<string, T | null>> {
  try {
    const promises = keyList.map(async (key) => {
      const value = await localforage.getItem<T>(key);
      return { key, value };
    });
    const results = await Promise.all(promises);
    return results.reduce(
      (acc, { key, value }) => {
        acc[key] = value;
        return acc;
      },
      {} as Record<string, T | null>,
    );
  } catch (error) {
    logger.error('[Storage] 批量获取数据失败', error);
    return {};
  }
}

/**
 * 批量删除数据
 * @param keyList 要删除的键名数组
 * @returns 是否全部删除成功
 */
export async function removeMultiple(keyList: string[]): Promise<boolean> {
  try {
    const promises = keyList.map((key) => localforage.removeItem(key));
    await Promise.all(promises);
    return true;
  } catch (error) {
    logger.error('[Storage] 批量删除数据失败', error);
    return false;
  }
}

/**
 * storage 对象导出（保持向后兼容）
 */
export const storage = {
  get,
  set,
  remove,
  clear,
  keys,
  length,
  iterate,
  has,
  driver,
  setMultiple,
  getMultiple,
  removeMultiple,
};

/**
 * 默认导出
 */
export default storage;
