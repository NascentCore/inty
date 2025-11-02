import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 创建聊天会话测试组件
 */
const ChatCreate: React.FC = () => {
  return (
    <TestWrapper
      title="创建聊天会话"
      inputs={[
        {
          name: 'agent_id',
          label: 'Agent ID',
          required: true,
          placeholder: '请输入 Agent ID',
        },
      ]}
      onTest={async (values) => {
        const client = await createIntyClient(true);
        const response = await client.api.v1.chats.create({
          agent_id: values.agent_id,
        });

        // 自定义成功日志
        logger.testDetail('Chat ID', response.id);
        logger.testDetail('Agent ID', response.agent_id);
        logger.testDetail('User ID', response.user_id);
        logger.testDetail('创建时间', response.created_at);

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default ChatCreate;

