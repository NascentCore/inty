import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 取消关注 Agent 测试组件
 */
const UnfollowAgent: React.FC = () => {
  return (
    <TestWrapper
      title="取消关注 Agent"
      description="取消关注指定的 Agent"
      inputs={[
        {
          name: 'agent_id',
          label: 'Agent ID',
          required: true,
          placeholder: '请输入要取关的 Agent ID',
        },
      ]}
      onTest={async (values) => {
        logger.testDetail('Agent ID', values.agent_id);

        const client = await createIntyClient(true);
        const response = await client.api.v1.ai.agents.unfollowAgent(values.agent_id);

        logger.testDetail('取关结果', response);

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default UnfollowAgent;
