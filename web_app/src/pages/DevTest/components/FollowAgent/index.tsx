import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 关注 Agent 测试组件
 */
const FollowAgent: React.FC = () => {
  return (
    <TestWrapper
      title="关注 Agent"
      description="关注指定的 Agent"
      inputs={[
        {
          name: 'agent_id',
          label: 'Agent ID',
          required: true,
          placeholder: '请输入要关注的 Agent ID',
        },
      ]}
      onTest={async (values) => {
        logger.testDetail('Agent ID', values.agent_id);

        const client = await createIntyClient(true);
        const response = await client.api.v1.ai.agents.followAgent(values.agent_id);

        logger.testDetail('关注结果', response);

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default FollowAgent;

