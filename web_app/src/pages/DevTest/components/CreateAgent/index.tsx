import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 创建 Agent 测试组件
 */
const CreateAgent: React.FC = () => {
  return (
    <TestWrapper
      title="创建 Agent"
      description="创建一个新的 AI Agent"
      inputs={[
        {
          name: 'name',
          label: 'Agent 名称',
          required: true,
          placeholder: '请输入 Agent 名称',
        },
        {
          name: 'gender',
          label: '性别',
          required: true,
          type: 'select',
          options: [
            { label: '女', value: 'FEMALE' },
            { label: '男', value: 'MALE' },
          ],
        },
        {
          name: 'intro',
          label: '简介',
          required: false,
          placeholder: '请输入简介',
        },
        {
          name: 'personality',
          label: '性格特点',
          required: false,
          placeholder: '如: 友善、耐心、专业',
        },
        {
          name: 'scenario',
          label: '背景设定',
          required: false,
          placeholder: '请输入背景设定',
        },
        {
          name: 'opening',
          label: '开场白',
          required: false,
          placeholder: '请输入开场白',
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
          defaultValue: 'PUBLIC',
        },
      ]}
      onTest={async (values) => {
        const params: any = {
          name: values.name,
          gender: values.gender,
        };

        // 添加可选字段
        if (values.intro) params.intro = values.intro;
        if (values.personality) params.personality = values.personality;
        if (values.scenario) params.scenario = values.scenario;
        if (values.opening) params.opening = values.opening;
        if (values.visibility) params.visibility = values.visibility;

        logger.testDetail('请求参数', params);

        const client = await createIntyClient(true);
        const response = await client.api.v1.ai.agents.create(params);

        // 自定义成功日志
        if (response.data) {
          logger.testDetail('Agent ID', response.data.id);
          logger.testDetail('Agent 名称', response.data.name);
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default CreateAgent;
