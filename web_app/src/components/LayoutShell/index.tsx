/**
 * LayoutShell 两栏布局容器
 *
 * 用途：提供固定侧边栏 + 主体内容的两栏布局骨架
 * 使用示例：
 * ```tsx
 * <LayoutShell sider={<SidebarContent />}>
 *   <Outlet />
 * </LayoutShell>
 * ```
 *
 * Props 说明：
 * - sider: React.ReactNode - 左侧区域内容
 * - children: React.ReactNode - 右侧主体内容
 *
 * 注意事项：
 * - 自带固定侧边栏宽度 280px
 * - 与 PageHeader（固定顶部 70px）配合使用
 * - CREATED_BY_AGENT
 */

import React from 'react';
import './index.less';

export interface ILayoutShellProps {
  /** 左侧区域内容 */
  sider: React.ReactNode;
  /** 右侧主体内容 */
  children: React.ReactNode;
}

const LayoutShell: React.FC<ILayoutShellProps> = ({ sider, children }) => {
  return (
    <div className="layout-shell">
      <div className="layout-shell-sider">{sider}</div>
      <div className="layout-shell-main">{children}</div>
    </div>
  );
};

export default LayoutShell;
