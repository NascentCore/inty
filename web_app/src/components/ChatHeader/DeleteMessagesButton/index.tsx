/**
 * DeleteMessagesButton 删除聊天记录按钮组件
 *
 * 用途：删除当前 Agent 的所有聊天记录
 * 使用示例：
 * ```tsx
 * <DeleteMessagesButton agentId={agent.id} />
 * ```
 */

import { Trash2 } from 'lucide-react';
import { useModel } from '@umijs/max';
import { Modal } from 'antd';
import React, { useState } from 'react';
import Icon from '@/components/Icon';
import { clearMessages, getChatMessages } from '@/http/api/chat';
import './index.less';

export interface DeleteMessagesButtonProps {
  agentId: string;
}

/**
 * DeleteMessagesButton 组件
 */
const DeleteMessagesButton: React.FC<DeleteMessagesButtonProps> = ({ agentId }) => {
  const { refreshMessages } = useModel('chat');
  const [clearing, setClearing] = useState(false);

  const handleClearMessages = async () => {
    Modal.confirm({
      title: '确认删除所有聊天记录？',
      content: '此操作将删除与该 Agent 的所有聊天记录，删除后无法恢复。',
      okText: '确认删除',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          setClearing(true);
          // 先获取完整的聊天记录
          const data = await getChatMessages(agentId, { limit: 100, order: 'desc' });
          // 找到用户发送的第一条消息的 id
          const userMessages = data.messages.filter((m: any) => m.role === 'user');
          if (userMessages.length === 0) return;
          const firstUserMessage = userMessages[userMessages.length - 1];
          await clearMessages(agentId, { message_id: firstUserMessage.id });
          // 刷新消息列表
          await refreshMessages(agentId);
        } catch (error) {
          console.error('删除聊天记录失败:', error);
        } finally {
          setClearing(false);
        }
      },
    });
  };

  return (
    <button
      className="delete-all-button"
      type="button"
      title="删除所有聊天记录"
      onClick={handleClearMessages}
      disabled={clearing}
    >
      <Icon icon={Trash2} size={20} />
    </button>
  );
};

export default DeleteMessagesButton;
