import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 获取聊天设置测试组件
 */
const ChatSettings: React.FC = () => {
  return (
    <TestWrapper
      title="获取聊天设置"
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
        const response = await client.api.v1.chats.agents.getSettings(values.agent_id);

        // 自定义成功日志
        logger.testDetail('Voice ID', response.voice_id);
        logger.testDetail('自动语音', response.auto_voice);
        logger.testDetail('完整数据', response);

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default ChatSettings;
