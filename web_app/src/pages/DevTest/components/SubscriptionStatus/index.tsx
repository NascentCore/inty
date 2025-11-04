import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 获取订阅状态测试组件
 */
const SubscriptionStatus: React.FC = () => {
  return (
    <TestWrapper
      title="获取订阅状态"
      description="获取当前用户的订阅状态和权益信息"
      inputs={[]}
      onTest={async () => {
        const client = await createIntyClient(true);
        const response = await client.api.v1.subscription.getStatus();

        // 自定义成功日志
        if (response.data) {
          logger.testDetail('是否订阅', response.data.is_subscribed);
          logger.testDetail('订阅状态', response.data.subscription_status);
          logger.testDetail('聊天限制', response.data.chat_limit_per_day);
          logger.testDetail('Agent创建限制', response.data.agent_creation_24h_limit);
          logger.testDetail('剩余天数', response.data.remaining_days);
          logger.testDetail('自动续费', response.data.will_auto_renew);
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default SubscriptionStatus;
