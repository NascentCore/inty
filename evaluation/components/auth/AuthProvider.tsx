/**
 * 应用初始化组件
 * 提供用户认证上下文和应用初始化状态
 */

import React, { useEffect, useState, ReactNode, createContext, useContext } from "react";
import { Spin } from "antd";
import { useUser, UserProfile } from "../../hooks/useUser";

interface AuthContextType {
  user: UserProfile | null;
  loading: boolean;
  error: string | null;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAppLoading, setIsAppLoading] = useState(true);
  const { user, loading: userLoading, error, refreshUser } = useUser();

  // 组件挂载时初始化应用状态
  useEffect(() => {
    const initApp = async () => {
      try {
        console.log("🚀 初始化应用...");

        // 模拟一些初始化时间
        await new Promise((resolve) => setTimeout(resolve, 500));

        console.log("✅ 应用初始化完成");
      } catch (error) {
        console.error("应用初始化失败:", error);
      } finally {
        setIsAppLoading(false);
      }
    };

    initApp();
  }, []);

  // 显示加载状态
  if (isAppLoading || userLoading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        <Spin size="large" />
        <div style={{ color: "#666" }}>
          {isAppLoading ? "正在初始化应用..." : "正在加载用户信息..."}
        </div>
      </div>
    );
  }

  const contextValue: AuthContextType = {
    user,
    loading: userLoading,
    error,
    refreshUser,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthProvider;
