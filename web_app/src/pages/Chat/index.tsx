/**
 * Chat 聊天页面
 * 实现与 AI Agent 的对话功能
 */

import React, { useEffect, useCallback, useRef } from 'react';
import { useParams, history } from '@umijs/max';
import { useModel } from '@umijs/max';
import { ErrorAlert } from '@/components';
import {
  ChatHeader,
  MessageList,
  MessageInput,
  AgentDetailPanel,
} from './components';
import './index.less';

/**
 * 聊天页面
 */
const ChatPage: React.FC = () => {
  // 获取路由参数
  const { agentId } = useParams<{ agentId: string }>();

  // 使用 ref 跟踪上一次的 agentId，避免依赖项循环触发
  const prevAgentIdRef = useRef<string | undefined>(undefined);

  // 获取 chat model（聊天消息管理）
  const { messages, loading, sending, error, loadMessages, sendChatMessage, reset } =
    useModel('chat');

  // 获取 agent model（Agent 信息管理）
  const {
    currentAgent,
    detailLoading: agentLoading,
    loadAgentDetail,
  } = useModel('agent');

  /**
   * 页面初始化：加载 Agent 详情和聊天历史
   * 检测到 agentId 变化时，先清空消息列表，避免显示旧对话内容
   */
  useEffect(() => {
    if (!agentId) {
      return;
    }

    // 检测到 agentId 变化时，先清空消息列表（触发 loading 状态）
    if (prevAgentIdRef.current && prevAgentIdRef.current !== agentId) {
      reset();
    }

    // 更新 ref
    prevAgentIdRef.current = agentId;

    // 加载 Agent 详情
    loadAgentDetail(agentId);

    // 加载聊天历史（第1页，每页100条）
    loadMessages({
      agent_id: agentId,
      limit: 100,
      offset: 0,
      order: 'asc',
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId]); // 仅在 agentId 变化时执行

  /**
   * 处理发送消息
   */
  const handleSendMessage = useCallback(
    async (content: string) => {
      if (!agentId) {
        return;
      }

      try {
        await sendChatMessage(agentId, content);
      } catch (err) {
        console.error('发送消息失败:', err);
      }
    },
    [agentId, sendChatMessage],
  );

  /**
   * 返回首页
   */
  const handleBack = useCallback(() => {
    history.push('/');
  }, []);

  return (
    <div className="chat-page">
      {/* 左侧：聊天区域 */}
      <div className="chat-main">
        {/* 顶部 Agent 信息 */}
        <ChatHeader
          agent={currentAgent}
          loading={agentLoading}
          onBack={handleBack}
        />

        {/* 消息列表 */}
        <div className="chat-content">
          <MessageList
            messages={messages}
            loading={loading}
            sending={sending}
            agentAvatar={currentAgent?.avatar}
            agentId={agentId}
          />
        </div>

        {/* 底部输入框 */}
        <div className="chat-footer">
          <MessageInput
            onSend={handleSendMessage}
            sending={sending}
            disabled={!currentAgent || agentLoading}
            placeholder={
              currentAgent ? `Chat with ${currentAgent.name}...` : 'Type a message...'
            }
          />
        </div>
      </div>

      {/* 错误提示 - 固定在页面顶部 */}
      {error && (
        <div className="chat-error-alert">
          <ErrorAlert message="Failed to send" description={error} type="error" />
        </div>
      )}

      {/* 右侧：角色详情面板 */}
      {currentAgent && <AgentDetailPanel agent={currentAgent} />}
    </div>
  );
};

export default ChatPage;
