import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 删除聊天会话测试组件
 */
const ChatDelete: React.FC = () => {
  return (
    <TestWrapper
      title="删除聊天会话"
      inputs={[
        {
          name: 'chat_id',
          label: 'Chat ID',
          required: true,
          placeholder: '请输入 Chat ID',
        },
      ]}
      onTest={async (values) => {
        const client = await createIntyClient(true);
        const response = await client.api.v1.chats.delete(values.chat_id);

        // 自定义成功日志
        logger.testDetail('Chat ID', response.id);
        logger.testDetail('Agent ID', response.agent_id);

        return response;
      }}
      buttonText="执行测试"
      buttonDanger
    />
  );
};

export default ChatDelete;

