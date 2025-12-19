/**
 * 聊天页面布局组件
 * 左侧：侧边栏菜单，右侧：聊天内容区
 * 顶部使用 ChatHeader 显示 Agent 信息
 */

import { Outlet } from '@umijs/max';
import React from 'react';
import SidebarContent from '@/components/SidebarContent';
import './index.less';
import BasePage from '@/components/BasePage';
import PageHeader from '@/components/PageHeader';
import ChatHeader from '@/components/ChatHeader';
import LayoutShell from '@/components/LayoutShell';

const ChatLayout: React.FC = () => {
  return (
    <BasePage>
      <div className="chat-layout layout-two-column">
        <PageHeader>
          <ChatHeader />
        </PageHeader>
        <LayoutShell sider={<SidebarContent />}>
          <Outlet />
        </LayoutShell>
      </div>
    </BasePage>
  );
};

export default ChatLayout;
