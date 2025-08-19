/**
 * 简化的应用初始化组件
 * 由于使用硬编码token，仅提供基本的应用初始化状态
 */

import React, { useEffect, useState, ReactNode } from "react";
import { Spin } from "antd";

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isLoading, setIsLoading] = useState(true);

  // 组件挂载时初始化应用状态
  useEffect(() => {
    const initApp = async () => {
      try {
        console.log("🚀 初始化应用...");
        
        // 模拟一些初始化时间
        await new Promise(resolve => setTimeout(resolve, 500));
        
        console.log("✅ 应用初始化完成");
      } catch (error) {
        console.error("应用初始化失败:", error);
      } finally {
        setIsLoading(false);
      }
    };

    initApp();
  }, []);

  // 显示加载状态
  if (isLoading) {
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
        <div style={{ color: "#666" }}>正在初始化应用...</div>
      </div>
    );
  }

  return <>{children}</>;
};

export default AuthProvider;
