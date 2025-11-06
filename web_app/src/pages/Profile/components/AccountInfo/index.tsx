/**
 * 账户信息组件
 *
 * 用途：展示用户账户信息（认证类型、注册时间）和退出登录功能
 * 使用示例：
 * ```tsx
 * <AccountInfo userProfile={userProfile} />
 * ```
 *
 * Props 说明：
 * - userProfile: IUserProfile - 用户信息对象
 */

import { useModel } from '@umijs/max';
import { Clock, LogOut, Shield } from 'lucide-react';
import React, { useState } from 'react';
import { Icon } from '@/components';
import type { IUserProfile } from '@/types';
import './index.less';

interface IAccountInfoProps {
  /** 用户信息 */
  userProfile: IUserProfile;
}

/**
 * 账户信息组件
 */
const AccountInfo: React.FC<IAccountInfoProps> = ({ userProfile }) => {
  const { logout } = useModel('user');
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  /**
   * 格式化认证类型显示
   */
  const getAuthTypeText = (authType: string): string => {
    const authTypeMap: Record<string, string> = {
      GOOGLE: 'Google',
      PHONE: 'Phone',
      EMAIL: 'Email',
      GUEST: 'Guest',
    };
    return authTypeMap[authType] || authType;
  };

  /**
   * 处理退出登录
   */
  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
    } catch (error) {
      console.error('退出登录失败:', error);
    } finally {
      setIsLoggingOut(false);
    }
  };

  /**
   * 格式化日期显示
   */
  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch {
      return dateString;
    }
  };

  /**
   * 信息项组件
   */
  const InfoItem: React.FC<{
    icon: typeof Shield;
    label: string;
    value: string;
  }> = ({ icon, label, value }) => (
    <div className="account-info-item">
      <div className="account-label">
        <Icon icon={icon} size={18} color="#6366f1" />
        <span>{label}</span>
      </div>
      <div className="account-value">{value}</div>
    </div>
  );

  return (
    <div className="account-info-card">
      <h2 className="card-title">Account Information</h2>

      <div className="account-list">
        <InfoItem icon={Shield} label="Auth Type" value={getAuthTypeText(userProfile.auth_type)} />

        <InfoItem icon={Clock} label="Joined" value={formatDate(userProfile.created_at)} />
      </div>

      {/* 退出登录按钮 */}
      <button
        type="button"
        className="logout-button"
        onClick={handleLogout}
        disabled={isLoggingOut}
      >
        <Icon icon={LogOut} size={18} />
        <span>{isLoggingOut ? 'Logging out...' : 'Logout'}</span>
      </button>
    </div>
  );
};

export default AccountInfo;
