/**
 * ChatHeader 聊天页面头部组件
 *
 * 用途：显示 Agent 信息和返回按钮
 * 使用示例：
 * ```tsx
 * <ChatHeader />
 * ```
 *
 * 注意事项：
 * - 右侧放入 PageHeader 的 children 区域
 * - CREATED_BY_AGENT
 */

import { ArrowLeft, Bot } from 'lucide-react';
import { history, useModel } from '@umijs/max';
import React from 'react';
import Icon from '@/components/Icon';
import './index.less';

/**
 * ChatHeader 组件
 */
const ChatHeader: React.FC = () => {
  const { currentAgent: agent, detailLoading: loading } = useModel('agent');

  const handleBack = () => {
    history.push('/');
  };

  /**
   * 渲染加载状态
   */
  if (loading) {
    return (
      <div className="chat-header">
        <button className="back-button" onClick={handleBack} type="button" title="Back">
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
        <button className="back-button" onClick={handleBack} type="button" title="Back">
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
      <button className="back-button" onClick={handleBack} type="button" title="Back">
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
