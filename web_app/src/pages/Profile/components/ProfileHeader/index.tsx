/**
 * 个人信息头部组件
 * 
 * 用途：展示用户头像、昵称、用户 ID
 * 使用示例：
 * ```tsx
 * <ProfileHeader userProfile={userProfile} />
 * ```
 * 
 * Props 说明：
 * - userProfile: IUserProfile - 用户信息对象
 */

import React from 'react';
import { User } from 'lucide-react';
import { Icon } from '@/components';
import type { IUserProfile } from '@/types';
import './index.less';

interface IProfileHeaderProps {
  /** 用户信息 */
  userProfile: IUserProfile;
}

/**
 * 个人信息头部组件
 */
const ProfileHeader: React.FC<IProfileHeaderProps> = ({ userProfile }) => {
  /**
   * 渲染用户头像
   */
  const renderAvatar = () => {
    // 如果有头像 URL，显示图片
    if (userProfile.avatar) {
      return (
        <img
          src={userProfile.avatar}
          alt={userProfile.nickname || 'User avatar'}
          className="profile-avatar-image"
        />
      );
    }

    // 如果有昵称，显示首字母
    if (userProfile.nickname) {
      const firstLetter = userProfile.nickname.charAt(0).toUpperCase();
      return <div className="profile-avatar-placeholder">{firstLetter}</div>;
    }

    // 默认显示用户图标
    return (
      <div className="profile-avatar-placeholder">
        <Icon icon={User} size={48} color="#999" />
      </div>
    );
  };

  return (
    <div className="profile-header-card">
      {/* 头像 */}
      <div className="profile-avatar-container">{renderAvatar()}</div>

      {/* 用户信息 */}
      <div className="profile-info">
        <h1 className="profile-nickname">
          {userProfile.nickname || 'No nickname set'}
        </h1>
        <div className="profile-id">ID: {userProfile.readable_id}</div>
      </div>
    </div>
  );
};

export default ProfileHeader;

