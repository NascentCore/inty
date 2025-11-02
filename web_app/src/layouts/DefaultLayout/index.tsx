import React from 'react';
import { Outlet } from '@umijs/max';

/**
 * 默认布局组件
 * 不添加任何布局，直接展示内部内容
 */
const DefaultLayout: React.FC = () => {
  return <Outlet />;
};

export default DefaultLayout;
