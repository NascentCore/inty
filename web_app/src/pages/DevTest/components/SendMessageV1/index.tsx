import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 发送消息 V1 测试组件
 */
const SendMessageV1: React.FC = () => {
  return (
    <TestWrapper
      title="发送消息 (V1 API)"
      description="⚠️ 已废弃的 API，建议仅用于测试。可以处理包括图片在内的各种消息类型。"
      inputs={[
        {
          name: 'agent_id',
          label: 'Agent ID',
          required: true,
          placeholder: '请输入 Agent ID',
        },
        {
          name: 'content',
          label: '消息内容',
          required: true,
          placeholder: '请输入消息内容',
        },
        {
          name: 'stream',
          label: '是否流式响应',
          required: false,
          type: 'select',
          options: [
            { label: '否', value: 'false' },
            { label: '是', value: 'true' },
          ],
          defaultValue: 'false',
        },
        {
          name: 'language',
          label: '语言',
          required: false,
          placeholder: 'zh-CN',
        },
        {
          name: 'model',
          label: '模型',
          required: false,
          placeholder: '模型名称（可选）',
        },
      ]}
      onTest={async (values) => {
        const params: any = {
          messages: [
            {
              role: 'user',
              content: values.content,
            },
          ],
          stream: values.stream || false,
        };

        if (values.language) {
          params.language = values.language;
        }
        if (values.model) {
          params.model = values.model;
        }

        logger.testDetail('Agent ID', values.agent_id);
        logger.testDetail('请求参数', params);

        const client = await createIntyClient(true);
        const response = await client.api.v1.chats.createCompletion(values.agent_id, params);

        // 自定义成功日志
        if (response.data) {
          logger.testDetail('回复内容', response.data);
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default SendMessageV1;
