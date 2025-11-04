import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 检查应用版本测试组件
 */
const CheckVersion: React.FC = () => {
  return (
    <TestWrapper
      title="检查应用版本"
      description="检查应用版本更新"
      inputs={[
        {
          name: 'appVersionCode',
          label: 'App Version Code',
          required: true,
          type: 'number',
          placeholder: '如: 100',
          defaultValue: '100',
        },
        {
          name: 'appVersionName',
          label: 'App Version Name',
          required: false,
          placeholder: '如: 1.0.0',
          defaultValue: '1.0.0',
        },
      ]}
      onTest={async (values) => {
        const params = {
          appVersionCode: values.appVersionCode,
          appVersionName: values.appVersionName,
        };

        logger.testDetail('请求参数', params);

        const client = await createIntyClient(true);
        const response = await client.api.v1.version.check(params);

        // 自定义成功日志
        if (response.data) {
          logger.testDetail('当前版本', response.data.current_version);
          logger.testDetail('最新版本', response.data.latest_version);
          logger.testDetail('最低支持版本', response.data.minimum_version);
          logger.testDetail('需要更新', response.data.update_required);
          logger.testDetail('强制更新', response.data.force_update);
          logger.testDetail('下载地址', response.data.download_url);
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default CheckVersion;
