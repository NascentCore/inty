import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 更新用户资料测试组件
 */
const UpdateProfile: React.FC = () => {
  return (
    <TestWrapper
      title="更新用户资料"
      description="更新当前用户的个人资料信息"
      inputs={[
        {
          name: 'nickname',
          label: '昵称',
          required: false,
          placeholder: '请输入昵称',
        },
        {
          name: 'avatar',
          label: '头像URL',
          required: false,
          placeholder: '请输入头像URL',
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
          name: 'age_group',
          label: '年龄组',
          required: false,
          placeholder: '如: 25-34',
        },
        {
          name: 'description',
          label: '个人简介',
          required: false,
          placeholder: '请输入个人简介',
        },
        {
          name: 'email',
          label: '邮箱',
          required: false,
          placeholder: '请输入邮箱',
        },
        {
          name: 'phone',
          label: '手机号',
          required: false,
          placeholder: '请输入手机号',
        },
        {
          name: 'system_language',
          label: '系统语言',
          required: false,
          placeholder: 'zh-CN',
        },
      ]}
      onTest={async (values) => {
        // 过滤空值
        const params: any = {};
        Object.entries(values).forEach(([key, value]) => {
          if (value) {
            params[key] = value;
          }
        });

        logger.testDetail('请求参数', params);

        const client = await createIntyClient(true);
        const response = await client.api.v1.users.profile.update(params);

        // 自定义成功日志
        if (response.data) {
          logger.testDetail('更新后的用户信息', response.data);
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default UpdateProfile;

