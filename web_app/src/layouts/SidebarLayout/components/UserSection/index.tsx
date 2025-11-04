/**
 * 用户区域组件
 * 
 * 用途：显示用户头像和订阅按钮，位于侧边栏底部
 * 使用示例：
 * ```tsx
 * <UserSection 
 *   userProfile={userProfile}
 *   isRegistered={isRegistered}
 *   loading={loading}
 *   onSubscribeClick={handleSubscribe}
 * />
 * ```
 * 
 * Props 说明：
 * - userProfile: IUserProfile | null - 用户信息对象
 * - isRegistered: boolean - 是否为注册用户
 * - loading: boolean - 是否正在加载用户信息
 * - onSubscribeClick: () => void - 订阅按钮点击回调
 * 
 * 注意事项：
 * - 如果用户无头像，显示默认占位符（用户昵称首字母）
 * - 点击头像：非注册用户弹出登录弹窗，注册用户跳转个人中心
 */

import React from 'react';
import { history, useModel } from '@umijs/max';
import { User } from 'lucide-react';
import { Icon } from '@/components';
import { SubscribeButton } from '../index';
import type { IUserProfile } from '@/types';
import './index.less';

interface IUserSectionProps {
  /** 用户信息 */
  userProfile: IUserProfile | null;
  /** 是否为注册用户 */
  isRegistered?: boolean;
  /** 加载状态 */
  loading?: boolean;
  /** 订阅按钮点击回调 */
  onSubscribeClick?: () => void;
}

/**
 * 用户区域组件
 */
const UserSection: React.FC<IUserSectionProps> = ({
  userProfile,
  isRegistered = false,
  loading = false,
  onSubscribeClick,
}) => {
  // 获取 Google 登录弹窗控制
  const { show: showLoginModal } = useModel('googleLoginModal');
  /**
   * 渲染用户头像
   */
  const renderAvatar = () => {
    // 如果正在加载，显示加载占位符
    if (loading) {
      return (
        <div className="user-avatar-placeholder loading">
          <Icon icon={User} size={20} color="#666" />
        </div>
      );
    }

    // 如果是非注册用户（访客），显示访客图标
    if (!isRegistered) {
      return (
        <div className="user-avatar-placeholder guest">
          <Icon icon={User} size={20} color="#999" />
        </div>
      );
    }

    // 如果有头像 URL，显示图片
    if (userProfile?.avatar) {
      return (
        <img
          src={userProfile.avatar}
          alt={userProfile.nickname || '用户头像'}
          className="user-avatar-image"
        />
      );
    }

    // 如果有昵称，显示首字母
    if (userProfile?.nickname) {
      const firstLetter = userProfile.nickname.charAt(0).toUpperCase();
      return <div className="user-avatar-placeholder">{firstLetter}</div>;
    }

    // 默认显示用户图标
    return (
      <div className="user-avatar-placeholder">
        <Icon icon={User} size={20} color="#999" />
      </div>
    );
  };

  /**
   * 处理头像点击
   * - 如果是非注册用户（访客），弹出登录弹窗
   * - 如果是注册用户，跳转到个人中心
   */
  const handleAvatarClick = () => {
    if (!isRegistered) {
      // 非注册用户，显示登录弹窗
      showLoginModal();
    } else {
      // 注册用户，跳转个人中心
      history.push('/profile');
    }
  };

  return (
    <div className="user-section-wrapper">
      {/* 用户头像区域 */}
      <div className="user-avatar-container" onClick={handleAvatarClick}>
        {renderAvatar()}
      </div>

      {/* 订阅按钮 */}
      <SubscribeButton
        inline
        onClick={onSubscribeClick}
        disabled={loading}
      />
    </div>
  );
};

export default UserSection;

