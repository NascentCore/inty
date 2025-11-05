import { Switch } from 'antd';
import React, { useState } from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 更新聊天设置测试组件
 */
const UpdateChatSettings: React.FC = () => {
  const [autoVoice, setAutoVoice] = useState<boolean>(false);

  return (
    <div className="test-component">
      <h4>更新聊天设置</h4>

      {/* 自动语音开关 */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'block', marginBottom: 8 }}>自动语音:</div>
        <Switch
          checked={autoVoice}
          onChange={setAutoVoice}
          checkedChildren="开启"
          unCheckedChildren="关闭"
        />
      </div>

      <TestWrapper
        title=""
        inputs={[
          {
            name: 'agent_id',
            label: 'Agent ID',
            required: true,
            placeholder: '请输入 Agent ID',
          },
          {
            name: 'voice_id',
            label: 'Voice ID',
            placeholder: '请输入 Voice ID',
          },
        ]}
        onTest={async (values) => {
          const params: Record<string, unknown> = {
            auto_voice: autoVoice,
          };

          if (values.voice_id?.trim()) {
            params.voice_id = values.voice_id;
          }

          logger.testDetail('请求参数', {
            agent_id: values.agent_id,
            ...params,
          });

          const client = await createIntyClient(true);
          const response = await client.api.v1.chats.agents.updateSettings(values.agent_id, params);

          logger.testDetail('更新后的设置', response.data);

          return response;
        }}
        buttonText="执行测试"
      />
    </div>
  );
};

export default UpdateChatSettings;
