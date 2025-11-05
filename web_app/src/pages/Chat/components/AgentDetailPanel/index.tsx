/**
 * AgentDetailPanel 组件
 * 显示 Agent 的详细信息，包括背景图、名称、简介和标签
 */

import React from 'react';
import type { IAgent } from '@/types';
import './index.less';

/**
 * AgentDetailPanel 组件 Props
 */
interface IAgentDetailPanelProps {
  /** Agent 信息 */
  agent: IAgent;
}

/**
 * AgentDetailPanel 组件
 */
const AgentDetailPanel: React.FC<IAgentDetailPanelProps> = ({ agent }) => {
  return (
    <div className="agent-detail-panel">
      {/* 角色背景大图 */}
      <div
        className="agent-hero-image"
        style={{
          backgroundImage: agent.background ? `url(${agent.background})` : `url(${agent.avatar})`,
        }}
      >
        <div className="hero-overlay" />
      </div>

      {/* 角色信息 */}
      <div className="agent-info">
        {/* 角色名称 */}
        <h2 className="agent-name">{agent.name}</h2>

        {/* 简介 */}
        {agent.intro && (
          <div className="agent-intro">
            <p>{agent.intro}</p>
          </div>
        )}

        {/* 标签 */}
        {agent.tags && agent.tags.length > 0 && (
          <div className="agent-tags">
            {agent.tags.map((tag) => (
              <span key={tag} className="tag">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentDetailPanel;
