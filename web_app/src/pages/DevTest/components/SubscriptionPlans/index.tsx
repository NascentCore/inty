import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 订阅计划列表测试组件
 */
const SubscriptionPlans: React.FC = () => {
  return (
    <TestWrapper
      title="订阅计划列表"
      description="获取可用的订阅计划列表"
      inputs={[]}
      onTest={async () => {
        const client = await createIntyClient(true);
        const response = await client.api.v1.subscription.listPlans();

        // 自定义成功日志
        if (response.data) {
          logger.testDetail('计划数量', response.data.plans?.length);
          response.data.plans?.forEach((plan: any, index: number) => {
            logger.testDetail(`计划 ${index + 1}`, {
              name: plan.name,
              price: plan.price,
              type: plan.plan_type,
            });
          });
          logger.testDetail('当前订阅', response.data.current_subscription);
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default SubscriptionPlans;
