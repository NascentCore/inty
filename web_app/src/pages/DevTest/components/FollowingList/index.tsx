import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 关注列表测试组件
 */
const FollowingList: React.FC = () => {
  return (
    <TestWrapper
      title="关注列表"
      description="获取当前用户关注的 Agent 列表"
      inputs={[
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
          page: values.page || 1,
          page_size: values.page_size || 20,
        };

        logger.testDetail('请求参数', params);

        const client = await createIntyClient(true);
        const response = await client.api.v1.ai.agents.following(params);

        // 自定义成功日志
        if (response.data) {
          logger.testDetail('关注数量', response.data.list?.length);
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

export default FollowingList;

