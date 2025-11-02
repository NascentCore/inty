import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 获取设置测试组件
 */
const GetSettings: React.FC = () => {
  return (
    <TestWrapper
      title="获取设置"
      description="获取当前用户的设置信息"
      inputs={[]}
      onTest={async () => {
        const client = await createIntyClient(true);
        const response = await client.api.v1.settings.retrieve();

        // 自定义成功日志
        if (response) {
          logger.testDetail('语言', response.language);
          logger.testDetail('语音启用', response.voice_enabled);
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default GetSettings;

