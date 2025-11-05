/**
 * 用户状态管理
 * 管理用户信息、登录状态等
 */

import { useCallback, useState } from 'react';
import { getUserProfile } from '@/services/user';
import type { IUserProfile } from '@/types';

/**
 * 用户 Model 状态接口
 */
export interface IUserModelState {
  /** 用户详细信息 */
  userProfile: IUserProfile | null;
  /** 用户信息加载状态 */
  profileLoading: boolean;
  /** 错误信息 */
  error: string | null;
  /** 是否为注册用户（非访客） */
  isRegistered: boolean;
}

export default function useUserModel() {
  // 状态定义
  const [userProfile, setUserProfile] = useState<IUserProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * 退出登录
   * 清除用户信息
   */
  const logout = useCallback(async () => {
    try {
      // 重置状态
      setUserProfile(null);
      setError(null);
    } catch (err) {
      console.error('退出登录失败:', err);
      setError('退出登录失败');
    }
  }, []);

  /**
   * 清除错误信息
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * 获取用户详细信息
   * 调用 SDK API 获取当前用户的完整资料
   * @returns 是否成功获取
   */
  const fetchUserProfile = useCallback(async (): Promise<boolean> => {
    setProfileLoading(true);
    setError(null);

    try {
      const profile = await getUserProfile();

      if (profile) {
        setUserProfile(profile);
        return true;
      }

      setError('获取用户信息失败');
      return false;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '获取用户信息失败';
      setError(errorMsg);
      return false;
    } finally {
      setProfileLoading(false);
    }
  }, []);

  // 计算属性：是否为注册用户（非访客）
  const isRegistered = userProfile?.auth_type !== 'GUEST' && !!userProfile;

  return {
    // 状态
    userProfile,
    profileLoading,
    error,
    isRegistered,

    // 方法
    logout,
    clearError,
    fetchUserProfile,
  };
}
