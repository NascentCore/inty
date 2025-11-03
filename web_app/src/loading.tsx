/**
 * 全局路由切换加载组件
 * UmiJS 约定式路由切换时自动显示此组件
 */

import React from 'react';
import Loading from '@/components/Loading';

const GlobalLoading: React.FC = () => (
  <Loading tip="加载中..." fullscreen />
);

export default GlobalLoading;
