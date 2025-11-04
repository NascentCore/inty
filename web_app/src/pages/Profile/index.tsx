/**
 * 用户个人信息页面
 * 展示用户基础信息、账户信息
 */

import { EmptyState, Loading } from "@/components";
import { useModel } from "@umijs/max";
import React from "react";
import { AccountInfo, BasicInfo, LoginPanel, ProfileHeader } from "./components";
import "./index.less";

const ProfilePage: React.FC = () => {
  const { userProfile, profileLoading, error, isRegistered } = useModel("user");

  // 加载状态
  if (profileLoading) {
    return (
      <div className="profile-page">
        <Loading tip="Loading profile..." fullscreen />
      </div>
    );
  }

  // 错误状态
  if (error) {
    return (
      <div className="profile-page">
        <EmptyState description={error} />
      </div>
    );
  }

  // 非注册用户（访客）- 显示登录面板
  if (!isRegistered) {
    return (
      <div className="profile-page">
        <LoginPanel />
      </div>
    );
  }

  // 注册用户但无用户信息
  if (!userProfile) {
    return (
      <div className="profile-page">
        <EmptyState description="Unable to load profile" />
      </div>
    );
  }

  // 注册用户 - 显示完整个人信息
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
