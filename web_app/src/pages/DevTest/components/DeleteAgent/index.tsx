import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 删除 Agent 测试组件
 */
const DeleteAgent: React.FC = () => {
  return (
    <TestWrapper
      title="删除 Agent"
      description="⚠️ 警告：删除后无法恢复"
      inputs={[
        {
          name: 'agent_id',
          label: 'Agent ID',
          required: true,
          placeholder: '请输入要删除的 Agent ID',
        },
      ]}
      onTest={async (values) => {
        logger.testDetail('Agent ID', values.agent_id);

        const client = await createIntyClient(true);
        const response = await client.api.v1.ai.agents.delete(values.agent_id);

        logger.testDetail('删除结果', response);

        return response;
      }}
      buttonText="执行删除"
      buttonDanger
    />
  );
};

export default DeleteAgent;
