import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';
import { message } from 'antd';
import { saveToken } from '@/utils';

/**
 * Google 登录测试组件
 */
const GoogleLogin: React.FC = () => {
  return (
    <TestWrapper
      title="Google 登录"
      description="使用 Google 账号登录"
      inputs={[
        {
          name: 'id_token',
          label: 'Google ID Token',
          required: true,
          placeholder: '请输入 Google ID Token',
        },
        {
          name: 'age_group',
          label: '年龄组',
          required: false,
          placeholder: '如: 25-34',
        },
        {
          name: 'gender',
          label: '性别',
          required: false,
          type: 'select',
          options: [
            { label: '男', value: 'MALE' },
            { label: '女', value: 'FEMALE' },
            { label: '其他', value: 'OTHER' },
          ],
        },
        {
          name: 'system_language',
          label: '系统语言',
          required: false,
          placeholder: 'zh-CN',
          defaultValue: 'zh-CN',
        },
      ]}
      onTest={async (values) => {
        const params: any = {
          id_token: values.id_token,
        };

        // 添加用户信息（如果有）
        if (values.age_group || values.gender || values.system_language) {
          params.user_info = {
            age_group: values.age_group,
            gender: values.gender,
            system_language: values.system_language || 'zh-CN',
          };
        }

        logger.testDetail('请求参数', params);

        const client = await createIntyClient();
        const response = await client.api.v1.auth.google.login(params);

        // 自定义成功日志
        logger.testDetail('Token', response.data?.token);
        logger.testDetail('用户信息', response.data?.user);
        logger.testDetail('是否新用户', response.data?.user?.is_new_user);

        // 保存 token 到本地存储
        if (response.data?.token) {
          await saveToken(response.data.token);
        }

        return response;
      }}
      onSuccess={() => {
        message.success('Google 登录成功，Token 已保存');
      }}
      buttonText="执行测试"
    />
  );
};

export default GoogleLogin;

