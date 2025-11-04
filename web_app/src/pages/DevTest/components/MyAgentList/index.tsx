import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 我的 Agent 列表测试组件
 */
const MyAgentList: React.FC = () => {
  return (
    <TestWrapper
      title="我的 Agent 列表"
      description="获取当前用户创建的 Agent 列表"
      inputs={[
        {
          name: 'skip',
          label: '跳过数量',
          required: false,
          type: 'number',
          defaultValue: '0',
        },
        {
          name: 'limit',
          label: '返回数量',
          required: false,
          type: 'number',
          defaultValue: '20',
        },
      ]}
      onTest={async (values) => {
        const params = {
          skip: values.skip || 0,
          limit: values.limit || 20,
        };

        logger.testDetail('请求参数', params);

        const client = await createIntyClient(true);
        const response = await client.api.v1.ai.agents.list(params);

        // 自定义成功日志
        if (response.data) {
          logger.testDetail('Agent 数量', response.data.length);
          response.data.forEach((agent: any, index: number) => {
            logger.testDetail(`Agent ${index + 1}`, {
              id: agent.id,
              name: agent.name,
              status: agent.status,
            });
          });
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default MyAgentList;
