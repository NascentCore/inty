import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
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
        {
          name: 'language',
          label: '语言代码',
          required: false,
          placeholder: 'zh-CN',
        },
      ]}
      onTest={async (values) => {
        const params = {
          agent_id: values.agent_id,
          language: values.language,
        };

        logger.testDetail('Message ID', values.message_id);
        logger.testDetail('请求参数', params);

        const client = await createIntyClient(true);
        const response = await client.api.v1.chats.agents.generateMessageVoice(
          values.message_id,
          params,
        );

        logger.testDetail('语音生成结果', response);

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default GenerateMessageVoice;

