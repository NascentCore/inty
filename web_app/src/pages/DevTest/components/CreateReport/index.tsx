import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 提交举报测试组件
 */
const CreateReport: React.FC = () => {
  return (
    <TestWrapper
      title="提交举报"
      description="提交对用户或 Agent 的举报"
      inputs={[
        {
          name: 'target_type',
          label: '举报目标类型',
          required: true,
          type: 'select',
          options: [
            { label: 'Agent', value: 'AGENT' },
            { label: '用户', value: 'USER' },
          ],
        },
        {
          name: 'target_id',
          label: '目标ID',
          required: true,
          placeholder: '请输入目标ID',
        },
        {
          name: 'reason_ids',
          label: '举报原因ID（逗号分隔）',
          required: true,
          placeholder: '如: 1,2',
        },
        {
          name: 'description',
          label: '详细描述',
          required: false,
          placeholder: '请输入详细描述',
        },
      ]}
      onTest={async (values) => {
        const params: any = {
          target_type: values.target_type,
          target_id: values.target_id,
          reason_ids: values.reason_ids
            .split(',')
            .map((id: string) => Number.parseInt(id.trim(), 10)),
        };

        if (values.description) {
          params.description = values.description;
        }

        logger.testDetail('请求参数', params);

        const client = await createIntyClient(true);
        const response = await client.api.v1.report.create(params);

        logger.testDetail('举报结果', response);

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default CreateReport;
