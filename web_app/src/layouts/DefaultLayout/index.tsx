import React from 'react';
import { Outlet } from '@umijs/max';
import { GoogleLoginModal } from '@/components';

/**
 * 默认布局组件
 * 不添加任何布局，直接展示内部内容
 */
const DefaultLayout: React.FC = () => {
  return (
    <>
      <Outlet />
      {/* 全局 Google 登录弹窗 */}
      <GoogleLoginModal />
    </>
  );
};

export default DefaultLayout;
