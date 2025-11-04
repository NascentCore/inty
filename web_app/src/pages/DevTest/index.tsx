import {
  BellOutlined,
  CrownOutlined,
  LockOutlined,
  MessageOutlined,
  MobileOutlined,
  RobotOutlined,
  SearchOutlined,
  SettingOutlined,
  SoundOutlined,
  UploadOutlined,
  UserOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { Card, Input, Layout, Menu, Typography } from 'antd';
import React, { useState } from 'react';

// 导入所有测试组件
import {
  AgentDetail,
  // 聊天模块
  ChatCreate,
  ChatDelete,
  ChatList,
  ChatSettings,
  CheckDeletionEligibility,
  // 版本检查模块
  CheckVersion,
  // AI代理模块
  CreateAgent,
  // 举报模块
  CreateReport,
  DeleteAccount,
  DeleteAgent,
  FollowAgent,
  FollowingList,
  GenerateMessageVoice,
  // 设置模块
  GetSettings,
  GoogleLogin,
  // 认证模块
  GuestLogin,
  // 通知模块
  ListNotifications,
  // 语音合成模块
  ListVoices,
  MessageHistory,
  MyAgentList,
  RecommendAgents,
  SearchAgents,
  SendMessageV1,
  SendMessageV2,
  SubscriptionPlans,
  // 订阅模块
  SubscriptionStatus,
  SubscriptionUsage,
  TokenWriter,
  UnfollowAgent,
  UpdateAgent,
  UpdateChatSettings,
  UpdateProfile,
  UpdateSettings,
  // 文件上传模块
  UploadImage,
  // 用户模块
  UserProfile,
  VerifyPurchase,
} from './components';

import './index.less';

const { Sider, Content } = Layout;
const { Title, Paragraph } = Typography;

/**
 * 菜单项类型定义
 */
type MenuItem = Required<MenuProps>['items'][number];

/**
 * 组件映射类型
 */
interface IComponentMap {
  [key: string]: React.ComponentType;
}

/**
 * 开发测试页面
 * 用于测试 Inty SDK 的各项功能
 */
const DevTestPage: React.FC = () => {
  const [selectedKey, setSelectedKey] = useState<string>('auth-guest-login');
  const [searchValue, setSearchValue] = useState<string>('');

  /**
   * 组件映射表
   */
  const componentMap: IComponentMap = {
    // 认证模块
    'auth-guest-login': GuestLogin,
    'auth-google-login': GoogleLogin,
    'auth-token-writer': TokenWriter,

    // 用户模块
    'user-profile': UserProfile,
    'user-update-profile': UpdateProfile,
    'user-check-deletion': CheckDeletionEligibility,
    'user-delete-account': DeleteAccount,

    // AI代理模块
    'agent-create': CreateAgent,
    'agent-detail': AgentDetail,
    'agent-update': UpdateAgent,
    'agent-delete': DeleteAgent,
    'agent-my-list': MyAgentList,
    'agent-search': SearchAgents,
    'agent-recommend': RecommendAgents,
    'agent-follow': FollowAgent,
    'agent-unfollow': UnfollowAgent,
    'agent-following': FollowingList,

    // 聊天模块
    'chat-create': ChatCreate,
    'chat-list': ChatList,
    'chat-delete': ChatDelete,
    'chat-messages': MessageHistory,
    'chat-settings-get': ChatSettings,
    'chat-settings-update': UpdateChatSettings,
    'chat-generate-voice': GenerateMessageVoice,
    'chat-send-message-v1': SendMessageV1,
    'chat-send-message-v2': SendMessageV2,

    // 订阅模块
    'subscription-status': SubscriptionStatus,
    'subscription-usage': SubscriptionUsage,
    'subscription-plans': SubscriptionPlans,
    'subscription-verify': VerifyPurchase,

    // 设置模块
    'settings-get': GetSettings,
    'settings-update': UpdateSettings,

    // 举报模块
    'report-create': CreateReport,

    // 语音合成模块
    'voice-list': ListVoices,

    // 版本检查模块
    'version-check': CheckVersion,

    // 通知模块
    'notification-list': ListNotifications,

    // 文件上传模块
    'upload-image': UploadImage,
  };

  /**
   * 菜单项配置
   */
  const menuItems: MenuItem[] = [
    {
      key: 'auth',
      icon: <LockOutlined />,
      label: '认证模块',
      children: [
        { key: 'auth-guest-login', label: '游客登录' },
        { key: 'auth-google-login', label: 'Google 登录' },
        { key: 'auth-token-writer', label: 'Token 管理' },
      ],
    },
    {
      key: 'user',
      icon: <UserOutlined />,
      label: '用户模块',
      children: [
        { key: 'user-profile', label: '获取个人信息' },
        { key: 'user-update-profile', label: '更新用户资料' },
        { key: 'user-check-deletion', label: '检查删除资格' },
        { key: 'user-delete-account', label: '删除账户' },
      ],
    },
    {
      key: 'agent',
      icon: <RobotOutlined />,
      label: 'AI 代理模块',
      children: [
        { key: 'agent-create', label: '创建 Agent' },
        { key: 'agent-detail', label: '获取 Agent 详情' },
        { key: 'agent-update', label: '更新 Agent' },
        { key: 'agent-delete', label: '删除 Agent' },
        { key: 'agent-my-list', label: '我的 Agent 列表' },
        { key: 'agent-search', label: '搜索 Agent' },
        { key: 'agent-recommend', label: '推荐 Agent' },
        { key: 'agent-follow', label: '关注 Agent' },
        { key: 'agent-unfollow', label: '取消关注' },
        { key: 'agent-following', label: '关注列表' },
      ],
    },
    {
      key: 'chat',
      icon: <MessageOutlined />,
      label: '聊天模块',
      children: [
        { key: 'chat-create', label: '创建会话' },
        { key: 'chat-list', label: '会话列表' },
        { key: 'chat-delete', label: '删除会话' },
        { key: 'chat-messages', label: '消息历史' },
        { key: 'chat-settings-get', label: '获取聊天设置' },
        { key: 'chat-settings-update', label: '更新聊天设置' },
        { key: 'chat-generate-voice', label: '生成消息语音' },
        { key: 'chat-send-message-v1', label: '发送消息 (V1)' },
        { key: 'chat-send-message-v2', label: '发送消息 (V2)' },
      ],
    },
    {
      key: 'subscription',
      icon: <CrownOutlined />,
      label: '订阅模块',
      children: [
        { key: 'subscription-status', label: '获取订阅状态' },
        { key: 'subscription-usage', label: '获取使用统计' },
        { key: 'subscription-plans', label: '订阅计划列表' },
        { key: 'subscription-verify', label: '验证购买' },
      ],
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '设置模块',
      children: [
        { key: 'settings-get', label: '获取设置' },
        { key: 'settings-update', label: '更新设置' },
      ],
    },
    {
      key: 'report',
      icon: <WarningOutlined />,
      label: '举报模块',
      children: [{ key: 'report-create', label: '提交举报' }],
    },
    {
      key: 'voice',
      icon: <SoundOutlined />,
      label: '语音合成模块',
      children: [{ key: 'voice-list', label: '获取语音列表' }],
    },
    {
      key: 'version',
      icon: <MobileOutlined />,
      label: '版本检查模块',
      children: [{ key: 'version-check', label: '检查应用版本' }],
    },
    {
      key: 'notification',
      icon: <BellOutlined />,
      label: '通知模块',
      children: [{ key: 'notification-list', label: '获取通知列表' }],
    },
    {
      key: 'upload',
      icon: <UploadOutlined />,
      label: '文件上传模块',
      children: [{ key: 'upload-image', label: '上传图片' }],
    },
  ];

  /**
   * 过滤菜单项（支持搜索）
   */
  const filteredMenuItems = searchValue
    ? (menuItems
        .map((item) => {
          if (item && 'children' in item && item.children) {
            const filteredChildren = item.children.filter((child) => {
              if (child && 'label' in child) {
                const label = child.label;
                if (typeof label === 'string') {
                  return label.toLowerCase().includes(searchValue.toLowerCase());
                }
              }
              return false;
            });
            if (filteredChildren.length > 0) {
              return { ...item, children: filteredChildren };
            }
          }
          return null;
        })
        .filter((item) => item !== null) as MenuItem[])
    : menuItems;

  /**
   * 渲染当前选中的组件
   */
  const renderContent = () => {
    const Component = componentMap[selectedKey];
    if (!Component) {
      return (
        <Card>
          <Paragraph>请从左侧菜单选择要测试的功能</Paragraph>
        </Card>
      );
    }
    return <Component />;
  };

  return (
    <div className="dev-test-page">
      {/* 页面标题 */}
      <div className="page-header">
        <Title level={2}>🛠 Inty SDK 开发测试</Title>
        <Paragraph type="secondary">测试 Inty SDK 各项功能，结果将在浏览器控制台输出</Paragraph>
      </div>

      <Layout className="dev-test-layout">
        {/* 左侧菜单 */}
        <Sider width={260} className="dev-test-sider" theme="light">
          <div className="menu-search">
            <Input
              placeholder="搜索功能..."
              prefix={<SearchOutlined />}
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              allowClear
            />
          </div>
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            defaultOpenKeys={['auth']}
            items={filteredMenuItems}
            onClick={({ key }) => setSelectedKey(key)}
            className="dev-test-menu"
          />
        </Sider>

        {/* 右侧内容区 */}
        <Content className="dev-test-content">{renderContent()}</Content>
      </Layout>

      {/* 使用说明 */}
      <Card title="📖 使用说明" className="usage-tip">
        <Paragraph>1. 请先执行"游客登录"获取 Token，Token 会自动保存到本地存储</Paragraph>
        <Paragraph>2. 所有测试结果会输出到浏览器控制台（按 F12 打开）</Paragraph>
        <Paragraph>3. 测试前请确保填写必需的参数（如 agent_id、chat_id 等）</Paragraph>
        <Paragraph>4. 如果遇到认证错误，请重新执行"游客登录"</Paragraph>
      </Card>
    </div>
  );
};

export default DevTestPage;
