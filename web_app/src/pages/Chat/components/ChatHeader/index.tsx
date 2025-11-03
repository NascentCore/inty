/**
 * ChatHeader 聊天页面头部组件
 * 显示 Agent 信息和返回按钮
 */

import React from 'react';
import { ArrowLeft, Bot } from 'lucide-react';
import type { IAgent } from '@/types';
import { Icon } from '@/components';
import './index.less';

/**
 * ChatHeader 组件 Props
 */
interface IChatHeaderProps {
  /** Agent 信息 */
  agent: IAgent | null;
  /** 加载状态 */
  loading: boolean;
  /** 返回回调 */
  onBack: () => void;
}

/**
 * ChatHeader 组件
 */
const ChatHeader: React.FC<IChatHeaderProps> = ({ agent, loading, onBack }) => {
  /**
   * 渲染加载状态
   */
  if (loading) {
    return (
      <div className="chat-header">
        <button className="back-button" onClick={onBack} type="button" title="Back">
          <Icon icon={ArrowLeft} size={20} />
        </button>
        <div className="agent-info">
          <div className="agent-avatar-skeleton" />
          <div className="agent-details">
            <div className="agent-name-skeleton" />
            <div className="agent-intro-skeleton" />
          </div>
        </div>
      </div>
    );
  }

  /**
   * 渲染错误状态
   */
  if (!agent) {
    return (
      <div className="chat-header">
        <button className="back-button" onClick={onBack} type="button" title="Back">
          <Icon icon={ArrowLeft} size={20} />
        </button>
        <div className="agent-info">
          <div className="agent-error">Agent information not found</div>
        </div>
      </div>
    );
  }

  /**
   * 渲染正常状态
   */
  return (
    <div className="chat-header">
      <button className="back-button" onClick={onBack} type="button" title="Back">
        <Icon icon={ArrowLeft} size={20} />
      </button>
      <div className="agent-info">
        <div
          className="agent-avatar"
          style={{
            backgroundImage: agent.avatar ? `url(${agent.avatar})` : undefined,
          }}
        >
          {!agent.avatar && <Icon icon={Bot} size={24} />}
        </div>
        <div className="agent-details">
          <h2 className="agent-name">{agent.name}</h2>
          {agent.intro && <p className="agent-intro">{agent.intro}</p>}
        </div>
      </div>
    </div>
  );
};

export default ChatHeader;

