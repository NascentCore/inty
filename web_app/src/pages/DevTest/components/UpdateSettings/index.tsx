import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 更新设置测试组件
 */
const UpdateSettings: React.FC = () => {
  return (
    <TestWrapper
      title="更新设置"
      description="更新当前用户的设置"
      inputs={[
        {
          name: 'language',
          label: '语言',
          required: false,
          placeholder: 'zh-CN',
        },
        {
          name: 'voice_enabled',
          label: '是否启用语音',
          required: false,
          type: 'select',
          options: [
            { label: '启用', value: true },
            { label: '禁用', value: false },
          ],
        },
      ]}
      onTest={async (values) => {
        // 过滤空值
        const params: any = {};
        if (values.language) params.language = values.language;
        if (values.voice_enabled !== undefined) params.voice_enabled = values.voice_enabled;

        logger.testDetail('请求参数', params);

        const client = await createIntyClient(true);
        const response = await client.api.v1.settings.update(params);

        // 自定义成功日志
        if (response) {
          logger.testDetail('更新后的设置', response);
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default UpdateSettings;

