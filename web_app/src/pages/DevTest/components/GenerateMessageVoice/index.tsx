import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { generateMessageVoice } from '@/services/chat';
import { logger } from '@/utils/logger';

/**
 * 生成消息语音测试组件
 */
const GenerateMessageVoice: React.FC = () => {
  return (
    <TestWrapper
      title="生成消息语音"
      description="为指定消息生成语音"
      inputs={[
        {
          name: 'agent_id',
          label: 'Agent ID',
          required: true,
          placeholder: '请输入 Agent ID',
        },
        {
          name: 'message_id',
          label: 'Message ID',
          required: true,
          placeholder: '请输入 Message ID',
        },
      ]}
      onTest={async (values) => {
        logger.testDetail('Message ID', values.message_id);
        logger.testDetail('Agent ID', values.agent_id);

        const response = await generateMessageVoice(
          values.message_id,
          values.agent_id,
        );

        logger.testDetail('语音生成结果', response);

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default GenerateMessageVoice;

