/**
 * CharacterCard 角色卡片组件
 * 简洁现代的卡片设计，背景图为主视觉
 */

import React from 'react';
import type { IAgent } from '@/types';
import './index.less';

/**
 * CharacterCard 组件 Props
 */
interface ICharacterCardProps {
  /** Agent 数据 */
  agent: IAgent;
  /** 开始对话回调 */
  onStartChat: (agent: IAgent) => void;
}

/**
 * CharacterCard 组件
 */
const CharacterCard: React.FC<ICharacterCardProps> = ({ agent, onStartChat }) => {
  /**
   * 处理卡片点击 - 直接开始对话
   */
  const handleCardClick = () => {
    onStartChat(agent);
  };

  /**
   * 获取背景图 URL
   */
  const getBackgroundImage = () => {
    return agent.background || agent.avatar || '';
  };

  return (
    <div className="character-card" onClick={handleCardClick}>
      {/* 背景图 - 撑满整个卡片 */}
      <div
        className="card-background"
        style={{
          backgroundImage: getBackgroundImage()
            ? `url(${getBackgroundImage()})`
            : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        }}
      />

      {/* 渐变遮罩 - 保证文字可读性 */}
      <div className="card-overlay" />

      {/* 已关注标签 - 右上角 */}
      {agent.is_followed && (
        <div className="followed-badge">
          <span>✓</span>
          <span>Following</span>
        </div>
      )}

      {/* 简介 - hover 时显示 */}
      <p className="character-description">{agent.intro || agent.opening || 'No description'}</p>

      {/* Chat Now 按钮 - hover 时显示 */}
      <button className="chat-button" type="button">
        Chat Now
      </button>

      {/* 基础信息 - 底部角色名称 */}
      <div className="card-basic-info">
        <h3 className="character-name">{agent.name}</h3>
      </div>
    </div>
  );
};

export default CharacterCard;
