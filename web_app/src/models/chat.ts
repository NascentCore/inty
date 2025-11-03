/**
 * 聊天状态管理
 * 管理聊天消息、历史记录等
 */

import { useState, useCallback } from 'react';
import { getChatMessages, sendMessage } from '@/services/chat';
import type { IMessage, IGetChatMessagesRequest } from '@/types';

/**
 * 聊天 Model 状态接口
 */
export interface IChatModelState {
  /** 消息列表 */
  messages: IMessage[];
  /** 当前 Agent ID */
  currentAgentId: string | null;
  /** 加载状态 */
  loading: boolean;
  /** 发送中状态 */
  sending: boolean;
  /** 错误信息 */
  error: string | null;
  /** 分页信息 */
  pagination: {
    hasMore: boolean;
    total: number;
    page: number;
    limit: number;
    offset: number;
  };
}

export default function useChatModel() {
  // 状态定义
  const [messages, setMessages] = useState<IMessage[]>([]);
  const [currentAgentId, setCurrentAgentId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [sending, setSending] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState({
    hasMore: false,
    total: 0,
    page: 1,
    limit: 20,
    offset: 0,
  });

  /**
   * 加载聊天消息
   * @param params 请求参数
   */
  const loadMessages = useCallback(
    async (params: IGetChatMessagesRequest) => {
      setLoading(true);
      setError(null);

      try {
        const data = await getChatMessages(params);

        // 如果是第一页，直接替换列表；否则追加到列表（用于加载更多）
        if (params.offset === 0) {
          setMessages(data.messages);
        } else {
          setMessages((prev) => [...prev, ...data.messages]);
        }

        // 更新分页信息
        setPagination({
          hasMore: data.has_more,
          total: data.total,
          page: data.page,
          limit: data.limit,
          offset: data.offset,
        });

        // 更新当前 Agent ID
        setCurrentAgentId(params.agent_id);

        // 输出到控制台
        console.log('聊天消息加载成功:', {
          agentId: params.agent_id,
          messageCount: data.messages.length,
          total: data.total,
          hasMore: data.has_more,
          messages: data.messages,
        });

        return data;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : '加载消息失败';
        setError(errorMsg);
        console.error('加载聊天消息失败:', err);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  /**
   * 刷新消息列表
   * 重新加载第一页
   */
  const refreshMessages = useCallback(
    async (agentId: string) => {
      return await loadMessages({
        agent_id: agentId,
        limit: 20,
        offset: 0,
        order: 'desc',
      });
    },
    [loadMessages],
  );

  /**
   * 加载更多消息
   * 加载下一页
   */
  const loadMoreMessages = useCallback(async () => {
    if (!currentAgentId || !pagination.hasMore) {
      return null;
    }
    return await loadMessages({
      agent_id: currentAgentId,
      limit: pagination.limit,
      offset: pagination.offset + pagination.limit,
      order: 'desc',
    });
  }, [loadMessages, currentAgentId, pagination]);

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
    setMessages([]);
    setCurrentAgentId(null);
    setLoading(false);
    setSending(false);
    setError(null);
    setPagination({
      hasMore: false,
      total: 0,
      page: 1,
      limit: 20,
      offset: 0,
    });
  }, []);

  /**
   * 发送消息
   * @param agentId Agent ID
   * @param content 消息内容
   */
  const sendChatMessage = useCallback(
    async (agentId: string, content: string) => {
      setSending(true);
      setError(null);

      try {
        // 立即添加用户消息到列表（乐观更新）
        const userMessage: IMessage = {
          id: `temp-${Date.now()}`,
          content,
          role: 'user',
          timestamp: new Date().toISOString(),
          created_at: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, userMessage]);

        // 调用 API 发送消息
        const response = await sendMessage(agentId, content);

        // 如果返回了 AI 回复，添加到消息列表
        if (response && response.content) {
          const assistantMessage: IMessage = {
            id: `assistant-${Date.now()}`,
            content: response.content,
            role: 'assistant',
            timestamp: new Date().toISOString(),
            created_at: new Date().toISOString(),
          };

          setMessages((prev) => [...prev, assistantMessage]);
        }

        return response;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : '发送消息失败';
        setError(errorMsg);
        console.error('发送消息失败:', err);
        // 移除乐观添加的用户消息
        setMessages((prev) => prev.slice(0, -1));
        throw err;
      } finally {
        setSending(false);
      }
    },
    [],
  );

  return {
    // 状态
    messages,
    currentAgentId,
    loading,
    sending,
    error,
    pagination,

    // 方法
    loadMessages,
    refreshMessages,
    loadMoreMessages,
    sendChatMessage,
    clearError,
    reset,
  };
}

