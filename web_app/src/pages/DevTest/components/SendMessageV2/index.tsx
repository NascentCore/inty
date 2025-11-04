import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 发送消息 V2 测试组件
 */
const SendMessageV2: React.FC = () => {
  return (
    <TestWrapper
      title="发送消息 (V2 API)"
      description="⚠️ 已废弃的 API，建议仅用于测试"
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
      ]}
      onTest={async (values) => {
        const params = {
          messages: [
            {
              role: 'user',
              content: values.content,
            },
          ],
          stream: values.stream || false,
        };

        logger.testDetail('Agent ID', values.agent_id);
        logger.testDetail('请求参数', params);

        const client = await createIntyClient(true);
        const response = await client.v2.chat.sendMessage(values.agent_id, params);

        // 自定义成功日志
        if (response.data) {
          logger.testDetail('回复内容', response.data.choices?.[0]?.message?.content);
          logger.testDetail('语音URL', response.data.choices?.[0]?.message?.audio_url);
          logger.testDetail('Token使用', response.data.usage);
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default SendMessageV2;
