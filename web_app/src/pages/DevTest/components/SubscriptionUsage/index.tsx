import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 获取使用统计测试组件
 */
const SubscriptionUsage: React.FC = () => {
  return (
    <TestWrapper
      title="获取使用统计"
      description="获取当前用户的使用统计信息"
      inputs={[]}
      onTest={async () => {
        const client = await createIntyClient(true);
        const response = await client.api.v1.subscription.getUsage();

        // 自定义成功日志
        if (response.data) {
          logger.testDetail('今日聊天次数', response.data.today_chat_count);
          logger.testDetail('今日限制', response.data.today_limit);
          logger.testDetail('Agent数量', response.data.agent_count);
          logger.testDetail('Agent限制', response.data.agent_limit);
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default SubscriptionUsage;

