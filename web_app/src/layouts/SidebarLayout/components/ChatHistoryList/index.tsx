/**
 * 聊天历史列表组件
 */

import { useLocation, useNavigate } from '@umijs/max';
import React from 'react';
import Loading from '@/components/Loading';
import type { IChatItem } from '@/types';
import { isChatActive } from '@/utils/sidebarHelpers';
import ChatHistoryItem from '../ChatHistoryItem';
import './index.less';

interface IChatHistoryListProps {
  chatList: IChatItem[];
  loading: boolean;
}

/**
 * 聊天历史列表
 */
const ChatHistoryList: React.FC<IChatHistoryListProps> = ({ chatList, loading }) => {
  const navigate = useNavigate();
  const location = useLocation();

  /**
   * 处理聊天项点击
   */
  const handleChatClick = (chat: IChatItem) => {
    navigate(`/chat/${chat.agent_id}`);
  };

  return (
    <div className="chat-history-list-wrapper">
      <div className="chat-history-header">
        <h3>Recent Chats</h3>
      </div>
      <div className="chat-history-list">
        {loading ? (
          <div className="chat-history-loading">
            <Loading size="small" />
          </div>
        ) : chatList.length > 0 ? (
          chatList.map((chat) => (
            <ChatHistoryItem
              key={chat.id}
              chat={chat}
              isActive={isChatActive(chat.agent_id, location.pathname)}
              onClick={handleChatClick}
            />
          ))
        ) : (
          <div className="chat-history-empty">
            <p>No chat history</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatHistoryList;
