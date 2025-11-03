import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 删除账户测试组件
 */
const DeleteAccount: React.FC = () => {
  return (
    <TestWrapper
      title="删除账户"
      description="⚠️ 警告：此操作不可逆！请谨慎操作"
      inputs={[
        {
          name: 'reason',
          label: '删除原因',
          required: false,
          placeholder: '请输入删除原因（可选）',
        },
      ]}
      onTest={async (values) => {
        const params: any = {};
        if (values.reason) {
          params.reason = values.reason;
        }

        logger.testDetail('请求参数', params);

        const client = await createIntyClient(true);
        const response = await client.api.v1.users.deleteAccount(params);

        // 自定义成功日志
        if (response.data) {
          logger.testDetail('删除成功', response.data.success);
          logger.testDetail('消息', response.data.message);
          logger.testDetail('用户ID', response.data.user_id);
          logger.testDetail('匿名化字段', response.data.anonymized_fields);
          logger.testDetail('删除日志ID', response.data.deletion_log_id);
        }

        return response;
      }}
      buttonText="执行删除"
      buttonDanger
    />
  );
};

export default DeleteAccount;

