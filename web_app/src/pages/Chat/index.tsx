/**
 * Chat 聊天页面
 * 实现与 AI Agent 的对话功能
 */

import { useModel, useParams } from '@umijs/max';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ErrorAlert } from '@/components';
import { SEASIDE_SCENE_BOOTSTRAP_MESSAGE_KEY } from '@/constants';
import { AgentDetailPanel, MessageInput, MessageList } from './components';
import './index.less';

/**
 * 聊天页面
 */
const ChatPage: React.FC = () => {
  // 获取路由参数
  const { agentId } = useParams<{ agentId: string }>();
  const [sceneHintVisible, setSceneHintVisible] = useState<boolean>(false);
  const [pendingSceneBootstrapMessage, setPendingSceneBootstrapMessage] = useState<string | null>(
    null,
  );

  // 使用 ref 跟踪上一次的 agentId，避免依赖项循环触发
  const prevAgentIdRef = useRef<string | undefined>(undefined);

  // 获取 chat model（聊天消息管理）
  const { messages, loading, sending, error, loadMessages, sendChatMessage, reset } =
    useModel('chat');

  // 获取 agent model（Agent 信息管理）
  const { currentAgent, detailLoading: agentLoading, loadAgentDetail } = useModel('agent');

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
   * 检测并消费场景启动消息：
   * 进入聊天页就立即展示“场景已启动”提示，不依赖消息加载状态
   */
  useEffect(() => {
    setSceneHintVisible(false);
    setPendingSceneBootstrapMessage(null);

    if (!agentId) {
      return;
    }

    const storageKey = `${SEASIDE_SCENE_BOOTSTRAP_MESSAGE_KEY}:${agentId}`;
    const bootstrapMessage = window.sessionStorage.getItem(storageKey);
    if (!bootstrapMessage) {
      return;
    }

    window.sessionStorage.removeItem(storageKey);
    setSceneHintVisible(true);
    setPendingSceneBootstrapMessage(bootstrapMessage);
  }, [agentId]);

  /**
   * 发送场景开场白（一次性）：
   * 场景提示先展示，再尽力发送首条消息；失败也不影响提示可见性
   */
  useEffect(() => {
    if (!agentId || !pendingSceneBootstrapMessage || sending) {
      return;
    }

    const messageToSend = pendingSceneBootstrapMessage;
    setPendingSceneBootstrapMessage(null);

    sendChatMessage(agentId, messageToSend).catch((err) => {
      console.error('自动发送场景开场消息失败:', err);
    });
  }, [agentId, pendingSceneBootstrapMessage, sending, sendChatMessage]);

  return (
    <div className="chat-page">
      {/* 左侧：聊天区域 */}
      <div className="chat-main">
        {/* 消息列表 */}
        <div className="chat-content">
          {sceneHintVisible ? (
            <div className="scene-start-feedback" role="status">
              Seaside mood started. Your first romantic prompt is being delivered.
            </div>
          ) : null}
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
            placeholder={currentAgent ? `Chat with ${currentAgent.name}...` : 'Type a message...'}
          />
        </div>
      </div>
      <div className="chat-right">
        {/* 右侧：角色详情面板 */}
        {currentAgent && <AgentDetailPanel agent={currentAgent} />}
      </div>
    </div>
  );
};

export default ChatPage;
