import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 获取 Agent 详情测试组件
 */
const AgentDetail: React.FC = () => {
  return (
    <TestWrapper
      title="获取 Agent 详情"
      description="获取指定 Agent 的详细信息"
      inputs={[
        {
          name: 'agent_id',
          label: 'Agent ID',
          required: true,
          placeholder: '请输入 Agent ID',
        },
      ]}
      onTest={async (values) => {
        logger.testDetail('Agent ID', values.agent_id);

        const client = await createIntyClient(true);
        const response = await client.api.v1.ai.agents.retrieve(values.agent_id);

        // 自定义成功日志
        if (response) {
          logger.testDetail('Agent 名称', response.name);
          logger.testDetail('简介', response.intro);
          logger.testDetail('关注数', response.follower_count);
          logger.testDetail('是否已关注', response.is_followed);
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default AgentDetail;

