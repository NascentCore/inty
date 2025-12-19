/**
 * 聊天历史项组件
 */

import { Bot } from 'lucide-react';
import React from 'react';
import { Icon } from '@/components';
import type { IChatItem } from '@/types';
import { truncateMessage } from '@/utils/sidebarHelpers';
import './index.less';

interface IChatHistoryItemProps {
  chat: IChatItem;
  isActive: boolean;
  onClick: (chat: IChatItem) => void;
}

/**
 * 单个聊天历史项
 */
const ChatHistoryItem: React.FC<IChatHistoryItemProps> = ({ chat, isActive, onClick }) => {
  const handleClick = () => {
    onClick(chat);
  };

  return (
    <div className={`chat-history-item ${isActive ? 'active' : ''}`} onClick={handleClick}>
      <div className="chat-avatar">
        {chat.agent_avatar ? (
          <img src={chat.agent_avatar} alt={chat.agent_name} className="avatar-image" />
        ) : (
          <div className="avatar-placeholder">
            <Icon icon={Bot} size={16} />
          </div>
        )}
      </div>
      <div className="chat-info">
        <div className="chat-title">{chat.agent_name}</div>
        <div className="chat-message">{truncateMessage(chat.last_message, 30)}</div>
      </div>
    </div>
  );
};

export default ChatHistoryItem;
