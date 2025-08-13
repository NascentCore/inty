/**
 * 认证提供器组件
 * 在应用启动时自动进行游客认证
 */

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { Spin, message } from 'antd';
import authService from '../../services/auth';

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  userId: string | null;
  login: () => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);

  const login = async (): Promise<boolean> => {
    try {
      setIsLoading(true);
      const success = await authService.ensureAuthenticated();
      
      if (success) {
        setIsAuthenticated(true);
        setUserId(authService.getUserId());
        message.success('认证成功');
        return true;
      } else {
        message.error('认证失败，请刷新页面重试');
        return false;
      }
    } catch (error) {
      console.error('登录失败:', error);
      message.error('登录失败');
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    authService.clearAuth();
    setIsAuthenticated(false);
    setUserId(null);
    message.info('已退出登录');
  };

  // 组件挂载时自动检查认证状态
  useEffect(() => {
    const initAuth = async () => {
      try {
        console.log('🔐 初始化认证...');
        
        // 检查是否已经有token
        if (authService.isAuthenticated()) {
          console.log('✅ 发现已存在的认证token');
          setIsAuthenticated(true);
          setUserId(authService.getUserId());
        } else {
          console.log('🆕 未找到认证token，创建游客用户...');
          const success = await authService.ensureAuthenticated();
          
          if (success) {
            setIsAuthenticated(true);
            setUserId(authService.getUserId());
            console.log('✅ 游客认证成功');
          } else {
            console.error('❌ 游客认证失败');
            message.error('自动认证失败，请手动登录');
          }
        }
      } catch (error) {
        console.error('认证初始化失败:', error);
        message.error('认证初始化失败');
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const value: AuthContextType = {
    isAuthenticated,
    isLoading,
    userId,
    login,
    logout
  };

  // 显示加载状态
  if (isLoading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: '16px'
      }}>
        <Spin size="large" />
        <div style={{ color: '#666' }}>
          正在初始化认证...
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Hook for using auth context
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthProvider;