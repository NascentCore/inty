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
  const { chatList, loading, loadChatList, hasTried } = useModel('chatList');
  const { userProfile, profileLoading, fetchUserProfile } = useModel('user');

  // 初始化加载聊天列表与用户信息，仅在数据缺失时触发
  // 请求去重机制（在 chatList model 中实现）会确保相同参数的请求不会重复发起
  useEffect(() => {
    // 加载用户信息（如果数据缺失且未在加载中）
    if (!userProfile && !profileLoading) {
      fetchUserProfile();
    }
  }, [fetchUserProfile, profileLoading, userProfile]);

  // 加载聊天列表（单独处理，避免未登录时重复请求）
  useEffect(() => {
    // 如果用户信息还在加载中，等待加载完成
    if (profileLoading) {
      return;
    }

    // 如果用户信息已加载完成且为 null（未登录），不加载聊天列表
    if (!userProfile) {
      return;
    }

    // 用户已登录，加载聊天列表（如果数据缺失且未在加载中且未尝试过）
    if (chatList.length === 0 && !loading && !hasTried) {
      loadChatList({ page: 1, page_size: 10 });
    }
  }, [chatList.length, loadChatList, loading, profileLoading, userProfile, hasTried]);

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
