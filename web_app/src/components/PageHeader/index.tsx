/**
 * PageHeader 页面头部组件
 *
 * 用途：展示站点信息并承载右侧自定义内容
 * 使用示例：
 * ```tsx
 * <PageHeader>
 *   <ChatHeader />
 * </PageHeader>
 * ```
 *
 * Props 说明：
 * - children: React.ReactNode - 右侧自定义内容
 *
 * 注意事项：
 * - 保持高度 70px，左右留白与原 SidebarHeader 一致
 * - CREATED_BY_AGENT
 */

import React from 'react';
import SiteInfo from '@/components/SiteInfo';
import './index.less';

export interface IPageHeaderProps {
  /** 右侧区域渲染内容 */
  children?: React.ReactNode;
}

/**
 * 页面通用头部组件
 */
const PageHeader: React.FC<IPageHeaderProps> = ({ children }) => {
  return (
    <div className="page-header-wrapper">
      <div className="page-header">
        <SiteInfo />
        <div className="page-header-right">{children}</div>
      </div>
    </div>
  );
};

export default PageHeader;
