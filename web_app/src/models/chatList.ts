/**
 * 聊天列表状态管理
 * 管理最近对话列表
 */

import { useCallback, useRef, useState } from 'react';
import { getChatList } from '@/services';
import type { IChatItem, IChatListRequest } from '@/types';

/**
 * 聊天列表 Model 状态接口
 */
export interface IChatListModelState {
  /** 聊天列表 */
  chatList: IChatItem[];
  /** 加载状态 */
  loading: boolean;
  /** 错误信息 */
  error: string | null;
  /** 是否已尝试过加载（用于避免未登录时重复请求） */
  hasTried: boolean;
}

export default function useChatListModel() {
  // 状态定义
  const [chatList, setChatList] = useState<IChatItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [hasTried, setHasTried] = useState<boolean>(false);

  // 存储当前正在进行的请求 Promise 和参数，用于请求去重
  const pendingRequestRef = useRef<Promise<IChatItem[]> | null>(null);
  const pendingParamsRef = useRef<IChatListRequest | null>(null);

  /**
   * 加载聊天列表
   * 实现请求去重：如果已有相同参数的请求正在进行，直接返回该 Promise
   * @param params 请求参数
   */
  const loadChatList = useCallback(async (params: IChatListRequest = {}) => {
    // 生成请求参数的缓存键（用于判断是否为相同请求）
    const paramsKey = JSON.stringify(params);
    const pendingKey = pendingParamsRef.current ? JSON.stringify(pendingParamsRef.current) : null;

    // 如果存在相同参数的正在进行的请求，直接返回该 Promise
    if (pendingRequestRef.current && paramsKey === pendingKey) {
      return pendingRequestRef.current;
    }

    // 创建新的请求 Promise
    const requestPromise = (async () => {
      setLoading(true);
      setError(null);
      pendingParamsRef.current = params;

      try {
        const list = await getChatList(params);
        setChatList(list);
        setHasTried(true);

        console.log('聊天列表加载成功:', {
          count: list.length,
        });

        return list;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : '加载聊天列表失败';
        setError(errorMsg);
        setHasTried(true);
        console.error('加载聊天列表失败:', err);
        throw err;
      } finally {
        setLoading(false);
        pendingRequestRef.current = null;
        pendingParamsRef.current = null;
      }
    })();

    // 保存当前请求的 Promise
    pendingRequestRef.current = requestPromise;

    return requestPromise;
  }, []);

  /**
   * 刷新聊天列表
   */
  const refreshChatList = useCallback(async () => {
    await loadChatList({ page: 1, page_size: 100 });
  }, [loadChatList]);

  /**
   * 清除错误信息
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * 重置状态
   */
  const reset = useCallback(() => {
    setChatList([]);
    setLoading(false);
    setError(null);
    setHasTried(false);
  }, []);

  return {
    // 状态
    chatList,
    loading,
    error,
    hasTried,

    // 方法
    loadChatList,
    refreshChatList,
    clearError,
    reset,
  };
}
