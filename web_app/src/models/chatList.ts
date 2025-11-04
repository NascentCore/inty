/**
 * 聊天列表状态管理
 * 管理最近对话列表
 */

import { useState, useCallback } from 'react';
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
}

export default function useChatListModel() {
  // 状态定义
  const [chatList, setChatList] = useState<IChatItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * 加载聊天列表
   * @param params 请求参数
   */
  const loadChatList = useCallback(async (params: IChatListRequest = {}) => {
    setLoading(true);
    setError(null);

    try {
      const list = await getChatList(params);
      setChatList(list);

      console.log('聊天列表加载成功:', {
        count: list.length,
      });
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '加载聊天列表失败';
      setError(errorMsg);
      console.error('加载聊天列表失败:', err);
    } finally {
      setLoading(false);
    }
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
  }, []);

  return {
    // 状态
    chatList,
    loading,
    error,

    // 方法
    loadChatList,
    refreshChatList,
    clearError,
    reset,
  };
}

