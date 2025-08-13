/**
 * 评测系统主应用组件
 * 包含路由管理、导航菜单、全局状态管理
 */

import React, { useState, useEffect } from 'react';
import { Layout, Menu, Typography, Tooltip } from 'antd';
import {
  RobotOutlined,
  MessageOutlined,
  BarChartOutlined,
  HistoryOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { EvaluationPage } from './pages/EvaluationPage';
import { EvaluationHistoryPage } from './pages/EvaluationHistoryPage';
import { ChatPage } from './pages/ChatPage';
import AgentManagePage from './pages/AgentManagePage';
import PromptQueryPage from './pages/PromptQueryPage';

const { Sider, Content } = Layout;
const { Title, Text } = Typography;

type PageKey = 'evaluation' | 'history' | 'chat' | 'agents' | 'prompt-query';

interface NavigationItem {
  key: PageKey;
  icon: React.ReactNode;
  label: string;
  description: string;
}

export const App: React.FC = () => {
  // 状态管理
  const [currentPage, setCurrentPage] = useState<PageKey>('evaluation');
  const [collapsed, setCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // 响应式检测
  useEffect(() => {
    const checkScreenSize = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile && !collapsed) {
        setCollapsed(true);
      }
    };

    checkScreenSize();
    window.addEventListener('resize', checkScreenSize);

    return () => {
      window.removeEventListener('resize', checkScreenSize);
    };
  }, [collapsed]);

  // 应用加载完成后隐藏加载动画
  useEffect(() => {
    // 延迟一小段时间确保应用完全加载
    const timer = setTimeout(() => {
      if (typeof window !== 'undefined' && window.hideLoading) {
        window.hideLoading();
        console.log('应用加载完成，隐藏加载动画');
      }
    }, 500);

    return () => clearTimeout(timer);
  }, []);

  // 导航菜单配置
  const navigationItems: NavigationItem[] = [
    {
      key: 'evaluation',
      icon: <BarChartOutlined />,
      label: '智能体评测',
      description: '创建和管理智能体评测任务',
    },
    {
      key: 'history',
      icon: <HistoryOutlined />,
      label: '评测记录',
      description: '查看历史评测会话和结果',
    },
    {
      key: 'chat',
      icon: <MessageOutlined />,
      label: '单角色聊天',
      description: '与智能体进行一对一聊天',
    },
    {
      key: 'agents',
      icon: <RobotOutlined />,
      label: '智能体管理',
      description: '创建、编辑和管理智能体',
    },
    {
      key: 'prompt-query',
      icon: <SearchOutlined />,
      label: '提示词查询',
      description: '查询会话提示词和调试信息',
    },
  ];

  // 渲染页面内容
  const renderPageContent = () => {
    switch (currentPage) {
      case 'evaluation':
        return <EvaluationPage />;
      case 'history':
        return (
          <EvaluationHistoryPage
            onNavigateToEvaluation={() => setCurrentPage('evaluation')}
          />
        );
      case 'chat':
        return <ChatPage />;
      case 'agents':
        return <AgentManagePage />;
      case 'prompt-query':
        return <PromptQueryPage />;
      default:
        return null;
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 侧边导航 */}
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={280}
        collapsedWidth={80}
        style={{
          overflow: 'hidden',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
          boxShadow: '2px 0 8px 0 rgba(29, 35, 41, 0.05)',
          display: 'flex',
          flexDirection: 'column',
        }}
        theme="light"
        breakpoint="lg"
        onBreakpoint={broken => {
          if (broken) {
            setCollapsed(true);
          }
        }}
      >
        {/* Logo区域 */}
        <div
          style={{
            padding: collapsed ? '16px 12px' : '16px 24px',
            borderBottom: '1px solid #f0f0f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
          }}
        >
          <RobotOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
          {!collapsed && (
            <div style={{ marginLeft: '12px' }}>
              <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
                InTy 评测
              </Title>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                智能体评测系统
              </Text>
            </div>
          )}
        </div>

        {/* 导航菜单容器 */}
        <div
          style={{
            flex: 1,
            overflow: 'auto',
            paddingBottom: collapsed ? '20px' : '80px', // 为底部预留空间
          }}
        >
          <Menu
            mode="inline"
            selectedKeys={[currentPage]}
            style={{
              border: 'none',
              paddingTop: '16px',
              background: 'transparent',
            }}
          >
            {navigationItems.map(item => (
              <Tooltip
                key={item.key}
                title={collapsed ? item.label : ''}
                placement="right"
                overlayStyle={{
                  fontSize: '12px',
                  color: '#ffffff',
                }}
                overlayInnerStyle={{
                  color: '#ffffff',
                  backgroundColor: 'rgba(0, 0, 0, 0.85)',
                  borderRadius: '6px',
                  padding: '6px 8px',
                  border: 'none',
                  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
                }}
              >
                <Menu.Item
                  key={item.key}
                  icon={item.icon}
                  onClick={() => setCurrentPage(item.key)}
                  style={{
                    height: 'auto',
                    lineHeight: 'normal',
                    padding: collapsed ? '12px' : '12px 24px',
                    marginBottom: '4px',
                    borderRadius: '6px',
                    display: 'flex',
                    alignItems: 'flex-start',
                  }}
                >
                  <div
                    style={{
                      flex: 1,
                      minHeight: collapsed ? 'auto' : '40px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: collapsed ? 'center' : 'flex-start',
                    }}
                  >
                    <div
                      style={{
                        fontSize: '14px',
                        fontWeight: '500',
                        lineHeight: '1.4',
                        color: 'rgba(0, 0, 0, 0.85)',
                        marginBottom: collapsed ? '0' : '2px',
                      }}
                    >
                      {item.label}
                    </div>
                    {!collapsed && (
                      <div
                        style={{
                          fontSize: '11px',
                          lineHeight: '1.3',
                          color: 'rgba(0, 0, 0, 0.45)',
                          marginTop: '2px',
                        }}
                      >
                        {item.description}
                      </div>
                    )}
                  </div>
                </Menu.Item>
              </Tooltip>
            ))}
          </Menu>
        </div>

        {/* 底部区域 */}
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            background: 'inherit',
          }}
        >
          {/* 底部信息 */}
          {!collapsed && (
            <div
              style={{
                padding: '16px 24px',
                textAlign: 'center',
                borderTop: '1px solid #f0f0f0',
              }}
            >
              <Text type="secondary" style={{ fontSize: '11px' }}>
                InTy Backend v1.0.0
              </Text>
            </div>
          )}
        </div>
      </Sider>

      {/* 主内容区域 */}
      <Layout
        style={{
          marginLeft: isMobile ? 0 : collapsed ? 80 : 280,
          transition: 'margin-left 0.2s',
          minHeight: '100vh',
        }}
      >
        {/* 页面内容 */}
        <Content
          style={{
            background: '#f0f2f5',
            minHeight: '100vh',
            overflow: 'auto',
            position: 'relative',
          }}
        >
          {renderPageContent()}
        </Content>
      </Layout>
    </Layout>
  );
};
