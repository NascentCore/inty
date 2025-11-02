import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 搜索 Agent 测试组件
 */
const SearchAgents: React.FC = () => {
  return (
    <TestWrapper
      title="搜索 Agent"
      description="根据关键词搜索公开的 Agent"
      inputs={[
        {
          name: 'q',
          label: '搜索关键词',
          required: true,
          placeholder: '请输入搜索关键词',
        },
        {
          name: 'page',
          label: '页码',
          required: false,
          type: 'number',
          defaultValue: 1,
        },
        {
          name: 'page_size',
          label: '每页数量',
          required: false,
          type: 'number',
          defaultValue: 20,
        },
      ]}
      onTest={async (values) => {
        const params = {
          q: values.q,
          page: values.page || 1,
          page_size: values.page_size || 20,
        };

        logger.testDetail('请求参数', params);

        const client = await createIntyClient(true);
        const response = await client.api.v1.ai.agents.search(params);

        // 自定义成功日志
        if (response.data) {
          logger.testDetail('搜索结果数量', response.data.list?.length);
          response.data.list?.forEach((agent: any, index: number) => {
            logger.testDetail(`Agent ${index + 1}`, {
              id: agent.id,
              name: agent.name,
            });
          });
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default SearchAgents;

