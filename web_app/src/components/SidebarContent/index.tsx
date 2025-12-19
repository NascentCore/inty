/**
 * 侧边栏内容组件
 *
 * 用途：聚合侧边栏区域的发现按钮、聊天历史和用户区域，内部自行获取所需数据和处理事件
 * 使用示例：
 * ```tsx
 * <SidebarContent
 *   chatList={chatList}
 *   loading={loading}
 *   userProfile={userProfile}
 *   isRegistered={isRegistered}
 *   profileLoading={profileLoading}
 *   onDiscoverClick={handleDiscoverClick}
 *   onSubscribeClick={handleSubscribeClick}
 * />
 * ```
 *
 * Props 说明：
 * - chatList: IChatItem[] - 聊天历史列表数据
 * - loading: boolean - 聊天历史加载状态
 * - userProfile: IUserProfile | null - 用户信息
 * - isRegistered: boolean - 是否为注册用户
 * - profileLoading: boolean - 用户信息加载状态
 * - onDiscoverClick: () => void - Discover 按钮点击回调
 * - onSubscribeClick: () => void - 订阅按钮点击回调
 */
import { history, useModel } from '@umijs/max';
import React, { useCallback, useEffect } from 'react';
import ChatHistoryList from './components/ChatHistoryList';
import DiscoverButton from './components/DiscoverButton';
import UserSection from './components/UserSection';
import './index.less';

/**
 * 侧边栏内容组件
 */
const SidebarContent: React.FC = () => {
  const { chatList, loading, loadChatList } = useModel('chatList');
  const { userProfile, profileLoading, isRegistered, fetchUserProfile } = useModel('user');

  // 初始化加载聊天列表与用户信息，避免重复请求
  useEffect(() => {
    if (chatList.length === 0 && !loading) {
      loadChatList({ page: 1, page_size: 10 });
    }
    if (!userProfile && !profileLoading) {
      fetchUserProfile();
    }
  }, [chatList.length, fetchUserProfile, loadChatList, loading, profileLoading, userProfile]);

  const handleDiscoverClick = useCallback(() => {
    history.push('/');
  }, []);

  const handleSubscribeClick = useCallback(() => {
    history.push('/subscribe');
  }, []);

  return (
    <>
      {/* Discover 按钮 */}
      <DiscoverButton onClick={handleDiscoverClick} />

      {/* 聊天历史列表 */}
      <ChatHistoryList chatList={chatList} loading={loading} />

      {/* google 自定义广告 */}
      {/* <AdSidebar /> */}

      {/* 用户区域 - 底部（头像 + 订阅按钮） */}
      <UserSection
        userProfile={userProfile}
        isRegistered={isRegistered}
        loading={profileLoading}
        onSubscribeClick={handleSubscribeClick}
      />
    </>
  );
};

export default SidebarContent;
