/**
 * 用户个人信息页面
 * 展示用户基础信息、账户信息
 */

import React, { useEffect } from 'react';
import { useModel } from '@umijs/max';
import { Loading, EmptyState } from '@/components';
import { ProfileHeader, BasicInfo, AccountInfo } from './components';
import './index.less';

const ProfilePage: React.FC = () => {
  const { userProfile, profileLoading, error, fetchUserProfile } = useModel('user');

  // 组件加载时获取用户信息
  useEffect(() => {
    if (!userProfile) {
      fetchUserProfile();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 仅在组件首次加载时执行

  // 加载状态
  if (profileLoading) {
    return (
      <div className="profile-page">
        <Loading tip="Loading profile..." fullscreen />
      </div>
    );
  }

  // 错误状态
  if (error || !userProfile) {
    return (
      <div className="profile-page">
        <EmptyState description={error || 'Unable to load profile'} />
      </div>
    );
  }

  return (
    <div className="profile-page">
      <div className="profile-container">
        {/* 个人信息头部 */}
        <ProfileHeader userProfile={userProfile} />

        {/* 基础信息 */}
        <BasicInfo userProfile={userProfile} />

        {/* 账户信息 */}
        <AccountInfo userProfile={userProfile} />
      </div>
    </div>
  );
};

export default ProfilePage;

