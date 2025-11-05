/**
 * 左右布局组件（侧边栏布局）
 * 左侧：侧边栏菜单，右侧：主体内容区
 */

import { history, Outlet, useModel } from '@umijs/max';
import React, { useEffect } from 'react';
import { GoogleLoginModal } from '@/components';
import ChatHistoryList from './components/ChatHistoryList';
import DiscoverButton from './components/DiscoverButton';
import SidebarHeader from './components/SidebarHeader';
import UserSection from './components/UserSection';
import './index.less';

const SidebarLayout: React.FC = () => {
  // 获取聊天列表数据
  const { chatList, loading, loadChatList } = useModel('chatList');

  // 获取用户信息
  const { userProfile, profileLoading, isRegistered, fetchUserProfile } = useModel('user');

  // 组件加载时获取聊天列表和用户信息
  // 只在数据为空时才加载，避免路由切换时重复请求
  useEffect(() => {
    // 只在聊天列表为空且未加载时才请求
    if (chatList.length === 0 && !loading) {
      loadChatList({ page: 1, page_size: 10 });
    }

    // 只在用户信息为空且未加载时才请求
    if (!userProfile && !profileLoading) {
      fetchUserProfile();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 仅在组件首次加载时执行一次

  /**
   * 处理 Discover 按钮点击 - 跳转到首页
   */
  const handleDiscoverClick = () => {
    history.push('/');
  };

  /**
   * 处理订阅按钮点击
   */
  const handleSubscribeClick = () => {
    // TODO: 实现订阅功能
    console.log('Subscribe clicked');
  };

  return (
    <>
      <div className="sidebar-layout">
        {/* 左侧边栏 */}
        <aside className="sidebar-layout-aside">
          {/* 顶部 Header */}
          <SidebarHeader />

          {/* Discover 按钮 */}
          <DiscoverButton onClick={handleDiscoverClick} />

          {/* 聊天历史列表 */}
          <ChatHistoryList chatList={chatList} loading={loading} />

          {/* 用户区域 - 底部（头像 + 订阅按钮） */}
          <UserSection
            userProfile={userProfile}
            isRegistered={isRegistered}
            loading={profileLoading}
            onSubscribeClick={handleSubscribeClick}
          />
        </aside>

        {/* 右侧主体内容 */}
        <main className="sidebar-layout-main">
          <div className="main-content">
            <Outlet />
          </div>
        </main>
      </div>

      {/* 全局 Google 登录弹窗 */}
      <GoogleLoginModal />
    </>
  );
};

export default SidebarLayout;
