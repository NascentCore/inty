/**
 * MessageList 组件
 * 聊天消息列表展示
 */

import { MessageCircle } from 'lucide-react';
import React, { useEffect, useRef } from 'react';
import { Icon } from '@/components';
import { DEFAULT_AGENT_AVATAR } from '@/constants';
import type { IMessage } from '@/types';
import MessageItem from '../MessageItem';
import './index.less';

/**
 * MessageList 组件 Props
 */
interface IMessageListProps {
  /** 消息列表 */
  messages: IMessage[];
  /** 是否正在加载 */
  loading?: boolean;
  /** 是否正在发送消息 */
  sending?: boolean;
  /** AI Agent 头像 URL */
  agentAvatar?: string | null;
  /** Agent ID（用于生成语音） */
  agentId?: string;
}

/**
 * MessageList 组件
 */
const MessageList: React.FC<IMessageListProps> = ({
  messages,
  loading = false,
  sending = false,
  agentAvatar,
  agentId,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const resolvedAgentAvatar = agentAvatar || DEFAULT_AGENT_AVATAR;

  /**
   * 滚动到底部
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  /**
   * 当消息列表更新时，自动滚动到底部
   */
  useEffect(() => {
    scrollToBottom();
  }, [messages, sending]);

  /**
   * 渲染空状态
   */
  const renderEmptyState = () => {
    if (loading) {
      return (
        <div className="message-list-empty">
          <div className="loading-spinner">
            <div className="spinner" />
          </div>
          <p className="empty-text"></p>
        </div>
      );
    }

    return (
      <div className="message-list-empty">
        <div className="empty-icon">
          <Icon icon={MessageCircle} size={64} color="rgba(255, 255, 255, 0.5)" strokeWidth={1.5} />
        </div>
        <p className="empty-text">No messages</p>
        <p className="empty-hint">Send a message to start the conversation</p>
      </div>
    );
  };

  /**
   * 渲染发送中状态
   */
  const renderSendingIndicator = () => {
    if (!sending) {
      return null;
    }

    return (
      <div className="message-sending">
        <div className="sending-avatar" style={{ backgroundImage: `url(${resolvedAgentAvatar})` }} />
        <div className="sending-bubble">
          <div className="typing-indicator">
            <span />
            <span />
            <span />
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="message-list-container" ref={containerRef}>
      {messages.length === 0 && !loading ? (
        renderEmptyState()
      ) : (
        <div className="message-list">
          {loading && messages.length === 0 ? (
            renderEmptyState()
          ) : (
            <>
              {messages.map((message) => (
                <MessageItem
                  key={message.id}
                  message={message}
                  agentAvatar={resolvedAgentAvatar}
                  agentId={agentId}
                />
              ))}
              {renderSendingIndicator()}
            </>
          )}
          {/* 滚动锚点 */}
          <div ref={messagesEndRef} />
        </div>
      )}
    </div>
  );
};

export default MessageList;
