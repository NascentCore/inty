/**
 * BasePage 组件
 *
 * 用途：提供页面的统一外层容器，负责包裹页面内容，并承载全局公共逻辑（数据预取、全局弹窗、版本徽章）
 * 使用示例：
 * ```tsx
 * <BasePage>
 *   <YourPageContent />
 * </BasePage>
 * ```
 *
 * Props 说明：
 * - children: React.ReactNode - 需要被包裹的页面内容
 *
 * 注意事项：
 * - 仅提供结构容器，不包含样式与业务逻辑
 */

import { useEffect } from 'react';
import { useModel } from '@umijs/max';
import React from 'react';
import { GoogleLoginModal, VersionBadge } from '@/components';

/** BasePage 组件 Props */
interface IBasePageProps {
  /** 需要包裹的页面内容 */
  children: React.ReactNode;
}

/**
 * 提供统一的页面外层容器，仅负责结构包裹。
 * @param props 组件入参
 * @returns 页面外层容器节点
 */
const BasePage: React.FC<IBasePageProps> = ({ children }: IBasePageProps): React.ReactElement => {
  const { chatList, loading, loadChatList } = useModel('chatList');
  const { userProfile, profileLoading, fetchUserProfile } = useModel('user');

  // 初始化加载聊天列表与用户信息，仅在数据缺失时触发，避免重复请求
  useEffect(() => {
    if (chatList.length === 0 && !loading) {
      loadChatList({ page: 1, page_size: 10 });
    }
    if (!userProfile && !profileLoading) {
      fetchUserProfile();
    }
  }, [chatList.length, fetchUserProfile, loadChatList, loading, profileLoading, userProfile]);

  return (
    <div className="base-page-container">
      {children}
      {/* 全局 Google 登录弹窗 */}
      <GoogleLoginModal />
      {/* 版本号徽章 - 开发测试用 */}
      <VersionBadge />
    </div>
  );
};

export default BasePage;
