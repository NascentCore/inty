import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 更新 Agent 测试组件
 */
const UpdateAgent: React.FC = () => {
  return (
    <TestWrapper
      title="更新 Agent"
      description="更新 Agent 信息"
      inputs={[
        {
          name: 'agent_id',
          label: 'Agent ID',
          required: true,
          placeholder: '请输入 Agent ID',
        },
        {
          name: 'name',
          label: 'Agent 名称',
          required: false,
          placeholder: '请输入新名称',
        },
        {
          name: 'intro',
          label: '简介',
          required: false,
          placeholder: '请输入新简介',
        },
        {
          name: 'visibility',
          label: '可见性',
          required: false,
          type: 'select',
          options: [
            { label: '公开', value: 'PUBLIC' },
            { label: '私有', value: 'PRIVATE' },
          ],
        },
      ]}
      onTest={async (values) => {
        const { agent_id, ...updateParams } = values;
        
        // 过滤空值
        const params: any = {};
        Object.entries(updateParams).forEach(([key, value]) => {
          if (value) {
            params[key] = value;
          }
        });

        logger.testDetail('Agent ID', agent_id);
        logger.testDetail('更新参数', params);

        const client = await createIntyClient(true);
        const response = await client.api.v1.ai.agents.update(agent_id, params);

        // 自定义成功日志
        if (response) {
          logger.testDetail('更新后的 Agent', response);
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default UpdateAgent;

