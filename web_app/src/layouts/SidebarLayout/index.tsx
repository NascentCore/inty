/**
 * 侧边栏布局组件
 * 左侧：侧边栏菜单，右侧：主体内容区
 * 顶部使用 PageHeader 显示站点信息
 */

import { Outlet } from '@umijs/max';
import React from 'react';
import SidebarContent from '@/components/SidebarContent';
import './index.less';
import BasePage from '@/components/BasePage';
import PageHeader from '@/components/PageHeader';
import DownloadButton from '@/components/DownloadButton';
import LayoutShell from '@/components/LayoutShell';

const SidebarLayout: React.FC = () => {
  return (
    <BasePage>
      <div className="sidebar-layout layout-two-column">
        <PageHeader>
          <DownloadButton />
        </PageHeader>
        <LayoutShell sider={<SidebarContent />}>
          <Outlet />
        </LayoutShell>
      </div>
    </BasePage>
  );
};

export default SidebarLayout;
