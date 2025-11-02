/**
 * SidebarHeader 侧边栏顶部组件
 * 显示站点名称
 */

import React from 'react';
import { Sparkles } from 'lucide-react';
import { Icon } from '@/components';
import './index.less';

/**
 * SidebarHeader 组件
 */
const SidebarHeader: React.FC = () => {
  return (
    <div className="sidebar-header">
      {/* 站点名称 */}
      <div className="site-info">
        <div className="site-logo">
          <Icon icon={Sparkles} size={28} />
        </div>
        <h1 className="site-name">IntelliMate</h1>
      </div>
    </div>
  );
};

export default SidebarHeader;

