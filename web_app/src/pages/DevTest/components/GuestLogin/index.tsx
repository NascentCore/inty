import React, { useState } from 'react';
import { Button, Input, Space, message } from 'antd';
import TestWrapper from '@/components/TestWrapper';
import { getOrCreateDeviceId, createIntyClient, saveToken } from '@/utils';
import { logger } from '@/utils/logger';

/**
 * 游客登录测试组件
 * 注意：此组件因为有特殊的"自动填充"功能，暂时不完全使用 TestWrapper
 */
const GuestLogin: React.FC = () => {
  const [deviceId, setDeviceId] = useState<string>('');

  /**
   * 自动填充设备 ID
   */
  const handleAutoFillDeviceId = async () => {
    try {
      const id = await getOrCreateDeviceId();
      setDeviceId(id);
      message.success('已自动填充设备 ID');
    } catch (error: unknown) {
      logger.error('获取设备 ID 失败', error);
      message.error('获取设备 ID 失败');
    }
  };

  return (
    <div className="test-component">
      <h4>游客登录</h4>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <div>
          <label>Device ID (可选):</label>
          <Space.Compact style={{ width: '100%', marginTop: 8 }}>
            <Input
              placeholder="留空将自动生成"
              value={deviceId}
              onChange={(e) => setDeviceId(e.target.value)}
            />
            <Button onClick={handleAutoFillDeviceId}>自动填充</Button>
          </Space.Compact>
        </div>

        <TestWrapper
          title=""
          inputs={[
            {
              name: 'system_language',
              label: '系统语言',
              required: false,
              defaultValue: 'zh-CN',
              placeholder: 'zh-CN',
            },
          ]}
          onTest={async (values) => {
            // 如果没有填写 device_id，自动生成
            let finalDeviceId = deviceId;
            if (!finalDeviceId) {
              finalDeviceId = await getOrCreateDeviceId();
              setDeviceId(finalDeviceId);
            }

            const params = {
              device_id: finalDeviceId,
              system_language: values.system_language || 'zh-CN',
            };

            logger.testDetail('请求参数', params);

            const client = await createIntyClient();
            const response = await client.api.v1.auth.createGuest(params);

            // 自定义成功日志
            logger.testDetail('Token', response.data?.token);
            logger.testDetail('Guest ID', response.data?.guest_id);
            logger.testDetail('是否新用户', response.data?.is_new_guest);

            // 保存 token 到本地存储
            if (response.data?.token) {
              await saveToken(response.data.token);
            }

            return response;
          }}
          onSuccess={() => {
            message.success('游客登录成功，Token 已保存');
          }}
          buttonText="执行测试"
        />
      </Space>
    </div>
  );
};

export default GuestLogin;

