import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 检查账户删除资格测试组件
 */
const CheckDeletionEligibility: React.FC = () => {
  return (
    <TestWrapper
      title="检查账户删除资格"
      description="检查当前用户是否可以删除账户"
      inputs={[]}
      onTest={async () => {
        const client = await createIntyClient(true);
        const response = await client.api.v1.users.deletion.checkEligibility();

        // 自定义成功日志
        if (response.data) {
          logger.testDetail('是否可以删除', response.data.can_delete);
          logger.testDetail('有活跃订阅', response.data.active_subscription);
          logger.testDetail('错误信息', response.data.error_message);
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default CheckDeletionEligibility;
