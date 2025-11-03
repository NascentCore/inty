import React from 'react';
import TestWrapper from '@/components/TestWrapper';
import { createIntyClient } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 获取用户信息测试组件
 */
const UserProfile: React.FC = () => {
  return (
    <TestWrapper
      title="获取个人信息"
      description="需要先执行游客登录获取 Token"
      inputs={[]}
      onTest={async () => {
        const client = await createIntyClient(true);
        const response = await client.api.v1.users.profile.me();

        // 自定义成功日志
        if (response.data) {
          logger.testDetail('ID', response.data.id);
          logger.testDetail('昵称', response.data.nickname);
          logger.testDetail('邮箱', response.data.email);
          logger.testDetail('性别', response.data.gender);
          logger.testDetail('头像', response.data.avatar);
          logger.testDetail('认证类型', response.data.auth_type);
          logger.testDetail('创建时间', response.data.created_at);
        }

        return response;
      }}
      buttonText="执行测试"
    />
  );
};

export default UserProfile;

