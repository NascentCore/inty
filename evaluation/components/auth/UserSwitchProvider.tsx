/**
 * 用户切换上下文提供者
 * 管理管理员用户之间的切换
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { Inty } from "inty";

interface AdminUser {
  id: string;
  token: string;
  name: string;
  description: string;
}

interface UserSwitchContextType {
  currentUser: AdminUser | null;
  availableUsers: AdminUser[];
  switchUser: (userId: string) => void;
  refreshCurrentUser: () => Promise<void>;
  loading: boolean;
  error: string | null;
}

const UserSwitchContext = createContext<UserSwitchContextType | undefined>(undefined);

// 预定义的管理员用户
const ADMIN_USERS: AdminUser[] = [
  {
    id: "admin-001",
    token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTg0OTY0NTksInN1YiI6InVzZXItMDAxIn0.oyBJ_BQ5SsEzBiLlBrF3xcfCq4vprAiwn9dhebZU7Lo",
    name: "Admin 001",
    description: "管理员用户 001",
  },
  {
    id: "admin-002", 
    token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTg0OTY0NTksInN1YiI6InVzZXItMDFKV1ozNFk0RDFDOTJHRDg2QTVSNkVXWUoifQ.2gBnU8peKgYA9oVX_qTY9T3aGa4ZzqnhBaXl5tFO2Wc",
    name: "Admin 002",
    description: "管理员用户 002",
  },
];

interface UserSwitchProviderProps {
  children: ReactNode;
}

export const UserSwitchProvider: React.FC<UserSwitchProviderProps> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<AdminUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 从 localStorage 恢复当前用户
  useEffect(() => {
    const savedUserId = localStorage.getItem("currentAdminUserId");
    if (savedUserId) {
      const user = ADMIN_USERS.find(u => u.id === savedUserId);
      if (user) {
        setCurrentUser(user);
      } else {
        // 如果保存的用户不存在，使用第一个用户
        setCurrentUser(ADMIN_USERS[0]);
        localStorage.setItem("currentAdminUserId", ADMIN_USERS[0].id);
      }
    } else {
      // 如果没有保存的用户，使用第一个用户
      setCurrentUser(ADMIN_USERS[0]);
      localStorage.setItem("currentAdminUserId", ADMIN_USERS[0].id);
    }
    setLoading(false);
  }, []);

  // 切换用户
  const switchUser = (userId: string) => {
    const user = ADMIN_USERS.find(u => u.id === userId);
    if (user) {
      setCurrentUser(user);
      localStorage.setItem("currentAdminUserId", userId);
      setError(null);
    } else {
      setError("用户不存在");
    }
  };

  // 刷新当前用户信息
  const refreshCurrentUser = async () => {
    if (!currentUser) return;
    
    try {
      setLoading(true);
      setError(null);
      
      // 创建临时客户端来测试连接
      const tempClient = new Inty({
        baseURL: (globalThis as any).INTY_BASE_URL || "http://localhost:8000",
        apiKey: currentUser.token,
      });
      
      // 尝试获取用户信息来验证token
      await tempClient.api.v1.users.profile.retrieve();
      
      console.log(`✅ 用户 ${currentUser.name} 验证成功`);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "用户验证失败";
      setError(errorMessage);
      console.error(`❌ 用户 ${currentUser.name} 验证失败:`, err);
    } finally {
      setLoading(false);
    }
  };

  const contextValue: UserSwitchContextType = {
    currentUser,
    availableUsers: ADMIN_USERS,
    switchUser,
    refreshCurrentUser,
    loading,
    error,
  };

  return (
    <UserSwitchContext.Provider value={contextValue}>
      {children}
    </UserSwitchContext.Provider>
  );
};

export const useUserSwitch = (): UserSwitchContextType => {
  const context = useContext(UserSwitchContext);
  if (context === undefined) {
    throw new Error("useUserSwitch must be used within a UserSwitchProvider");
  }
  return context;
};

export default UserSwitchProvider;
