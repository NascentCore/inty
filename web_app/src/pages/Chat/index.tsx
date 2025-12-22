/**
 * Chat 聊天页面
 * 实现与 AI Agent 的对话功能
 */

import { useModel, useParams, useLocation } from '@umijs/max';
import React, { useCallback, useEffect, useRef, useMemo } from 'react';
import { ErrorAlert } from '@/components';
import Live2DViewer, { type ILive2DViewerRef } from '@/components/Live2DViewer';
import { logger } from '@/utils';
import { AgentDetailPanel, MessageInput, MessageList } from './components';
import './index.less';

/**
 * 聊天页面
 */
const ChatPage: React.FC = () => {
  // 获取路由参数
  const { agentId } = useParams<{ agentId: string }>();
  const location = useLocation();

  // 使用 ref 跟踪上一次的 agentId，避免依赖项循环触发
  const prevAgentIdRef = useRef<string | undefined>(undefined);

  // Live2D Viewer 引用
  const live2dViewerRef = useRef<ILive2DViewerRef | null>(null);

  // 跟踪已处理的消息 ID，避免重复触发动画
  const processedMessageIdsRef = useRef<Set<string | number>>(new Set());

  // 获取 chat model（聊天消息管理）
  const { messages, loading, sending, error, loadMessages, sendChatMessage, reset } =
    useModel('chat');

  // 获取 agent model（Agent 信息管理）
  const { currentAgent, detailLoading: agentLoading, loadAgentDetail } = useModel('agent');

  // 从 URL 查询参数中检查是否启用 Live2D
  const shouldShowLive2D = useMemo(() => {
    if (!location.search) {
      console.log('[ChatPage] shouldShowLive2D: location.search is empty');
      return false;
    }
    try {
      const searchParams = new URLSearchParams(location.search);
      const live2dParam = searchParams.get('live2d');
      const enabled = live2dParam === '1' || live2dParam === 'true';
      console.log('[ChatPage] shouldShowLive2D:', {
        search: location.search,
        live2dParam,
        enabled,
      });
      return enabled;
    } catch (err) {
      console.error('[ChatPage] shouldShowLive2D error:', err);
      return false;
    }
  }, [location.search]);

  // 根据 agentId (UUID) 计算对应的 Live2D 模型 URL
  // UUID 格式：776798cb-ba8c-4fb3-a4f7-dfc6c425f29c
  // 策略：取最后一位字符，按十六进制数字处理，对 2 取余
  const live2dModelUrl = useMemo(() => {
    if (!shouldShowLive2D) {
      console.log('[ChatPage] live2dModelUrl: shouldShowLive2D is false');
      return null;
    }
    if (!agentId) {
      console.log('[ChatPage] live2dModelUrl: agentId is missing');
      return null;
    }

    try {
      // 取 UUID 最后一位字符
      const lastChar = agentId.slice(-1);
      // 按十六进制数字解析（0-9, a-f, A-F）
      const hexValue = parseInt(lastChar, 16);

      if (isNaN(hexValue)) {
        console.log('[ChatPage] live2dModelUrl: lastChar is not a valid hex digit', { agentId, lastChar });
        return null;
      }

      // 对 2 取余决定使用哪个模型
      const remainder = hexValue % 2;

      // 根据余数返回对应的模型 URL
      // 0 -> 模型1 (haru), 1 -> 模型2 (Hiyori)
      const modelUrl = remainder === 0
        ? '/live2d-models/haru/Haru.model3.json'
        : '/live2d-models/Hiyori/Hiyori.model3.json';

      console.log('[ChatPage] live2dModelUrl:', {
        agentId,
        lastChar,
        hexValue,
        remainder,
        modelUrl,
      });

      return modelUrl;
    } catch (err) {
      console.error('[ChatPage] live2dModelUrl error:', err);
      return null;
    }
  }, [agentId, shouldShowLive2D]);

  /**
   * 获取随机 idle 动画组
   * 目前先随机选择一个，后续可以根据消息内容类别选择特定动画
   */
  const getRandomIdleMotion = useCallback((): { group: string; index?: number } | null => {
    if (!live2dViewerRef.current?.internalModel) {
      return null;
    }

    try {
      // 获取模型内部的 motion 设置
      const internalModel = live2dViewerRef.current.internalModel.internalModel as any;
      const motions = internalModel?.settings?.motions;

      if (!motions) return null;

      // 查找 idle 动画组
      const idleGroups = Object.keys(motions).filter((group) =>
        group.toLowerCase().includes('idle')
      );

      if (idleGroups.length === 0) {
        // 如果没有 idle 组，使用第一个可用的组
        const allGroups = Object.keys(motions);
        if (allGroups.length === 0) return null;

        const randomGroup = allGroups[Math.floor(Math.random() * allGroups.length)];
        const motionCount = motions[randomGroup]?.length || 0;
        const randomIndex = motionCount > 0 ? Math.floor(Math.random() * motionCount) : undefined;

        return { group: randomGroup, index: randomIndex };
      }

      // 随机选择一个 idle 组
      const randomIdleGroup = idleGroups[Math.floor(Math.random() * idleGroups.length)];
      const motionCount = motions[randomIdleGroup]?.length || 0;
      const randomIndex = motionCount > 0 ? Math.floor(Math.random() * motionCount) : undefined;

      return { group: randomIdleGroup, index: randomIndex };
    } catch (err) {
      console.warn('[ChatPage] 获取 idle 动画失败:', err);
      return null;
    }
  }, []);

  /**
   * 监听新消息，触发 Live2D 动画
   * 当收到新的 assistant 消息时，触发嘴巴动画和 motion 动画
   */
  useEffect(() => {
    if (!shouldShowLive2D || !live2dViewerRef.current) {
      return;
    }

    // 查找最新的 assistant 消息
    const latestAssistantMessage = [...messages]
      .reverse()
      .find((msg) => msg.role === 'assistant' && !processedMessageIdsRef.current.has(msg.id));

    if (!latestAssistantMessage || !latestAssistantMessage.content) {
      return;
    }

    // 标记消息已处理
    processedMessageIdsRef.current.add(latestAssistantMessage.id);

    // 触发嘴巴动画（根据文本长度）
    live2dViewerRef.current.speakText(latestAssistantMessage.content);

    // 触发随机 idle motion 动画
    const motion = getRandomIdleMotion();
    if (motion) {
      live2dViewerRef.current.motion(motion.group, motion.index);
    }

    console.log('[ChatPage] 触发 Live2D 动画:', {
      messageId: latestAssistantMessage.id,
      contentLength: latestAssistantMessage.content.length,
      motion: motion || 'none',
    });
  }, [messages, shouldShowLive2D, getRandomIdleMotion]);

  /**
   * 当 agentId 变化时，清空已处理的消息 ID 集合
   */
  useEffect(() => {
    processedMessageIdsRef.current.clear();
  }, [agentId]);

  /**
   * 调试：打印 Live2D 相关状态
   */
  useEffect(() => {
    logger.debug('[ChatPage] Live2D Debug Info:', {
      shouldShowLive2D,
      live2dModelUrl,
      agentId,
      currentAgent: !!currentAgent,
      locationSearch: location.search,
    });
  }, [shouldShowLive2D, live2dModelUrl, agentId, currentAgent, location.search]);

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

  return (
    <div className="chat-page">
      {/* 左侧：聊天区域 */}
      <div className="chat-main">
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
            placeholder={currentAgent ? `Chat with ${currentAgent.name}...` : 'Type a message...'}
          />
        </div>
      </div>
      <div className="chat-right">
        {/* 右侧：角色详情面板 */}
        {currentAgent && (
          <>
            <AgentDetailPanel agent={currentAgent} />
            {/* 叠加 Live2D 模型（仅在 URL 参数启用时显示） */}
            {shouldShowLive2D && live2dModelUrl && (
              <div className="chat-live2d-overlay">
                <Live2DViewer
                  ref={live2dViewerRef}
                  modelUrl={live2dModelUrl}
                  scale={0.2}
                  x={0}
                  y={0}
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default ChatPage;
