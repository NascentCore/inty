/**
 * 认证状态显示组件
 */

import React from 'react';
import { Card, Button, Space, Tag, Typography } from 'antd';
import { UserOutlined, LoginOutlined, LogoutOutlined } from '@ant-design/icons';
import { useAuth } from './AuthProvider';

const { Text } = Typography;

export const AuthStatus: React.FC = () => {
  const { isAuthenticated, userId, login, logout, isLoading } = useAuth();

  return (
    <Card 
      size="small" 
      title={
        <Space>
          <UserOutlined />
          认证状态
        </Space>
      }
      style={{ marginBottom: 16 }}
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <Text strong>状态: </Text>
          {isAuthenticated ? (
            <Tag color="green">已认证</Tag>
          ) : (
            <Tag color="red">未认证</Tag>
          )}
        </div>
        
        {userId && (
          <div>
            <Text strong>用户ID: </Text>
            <Text code>{userId}</Text>
          </div>
        )}
        
        <Space>
          {isAuthenticated ? (
            <Button 
              size="small" 
              icon={<LogoutOutlined />}
              onClick={logout}
            >
              退出登录
            </Button>
          ) : (
            <Button 
              type="primary"
              size="small" 
              icon={<LoginOutlined />}
              loading={isLoading}
              onClick={login}
            >
              游客登录
            </Button>
          )}
        </Space>
        
        <Text type="secondary" style={{ fontSize: 12 }}>
          评测系统使用游客模式进行认证，无需注册即可使用所有功能。
        </Text>
      </Space>
    </Card>
  );
};

export default AuthStatus;