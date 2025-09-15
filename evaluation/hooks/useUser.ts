/**
 * 用户信息管理 Hook
 * 用于获取和管理当前用户信息
 */

import { useState, useEffect, useCallback } from "react";
import { Inty } from "inty";
import type { User } from "inty/resources/api/v1/users/profile";

// 使用 inty_sdk 的 User 类型
export type UserProfile = User;

interface UseUserReturn {
  user: UserProfile | null;
  loading: boolean;
  error: string | null;
  refreshUser: () => Promise<void>;
}

// 创建 Inty 客户端实例
const intyClient = new Inty({
  apiKey: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODQzNjAyMjAsInN1YiI6InVzZXItMDFKV1ozNFk0RDFDOTJHRDg2QTVSNkVXWUoifQ.vsYKRvrCfxWgJ5wkTjAYby3RrIOm6P-9VbcCg4msjlM",
  baseURL: "http://localhost:8000",
});

export const useUser = (): UseUserReturn => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 获取用户信息
  const fetchUser = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const userProfile = await intyClient.api.v1.users.profile.retrieve();
      setUser(userProfile);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "获取用户信息失败";
      setError(errorMessage);
      console.error("获取用户信息失败:", err);
      // 不显示错误消息，因为这是后台操作
    } finally {
      setLoading(false);
    }
  }, []);

  // 刷新用户信息
  const refreshUser = useCallback(async () => {
    await fetchUser();
  }, [fetchUser]);

  // 组件挂载时获取用户信息
  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  return {
    user,
    loading,
    error,
    refreshUser,
  };
};
