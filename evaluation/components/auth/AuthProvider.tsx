/**
 * 认证提供器组件
 * 在应用启动时自动进行游客认证
 */

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from 'react';
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
    // 由于token已硬编码，直接返回成功
    setIsAuthenticated(true);
    setUserId('admin-user');
    message.success('认证成功');
    return true;
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

        // 由于token已硬编码，直接设置为已认证状态
        console.log('✅ 使用硬编码token，无需认证');
        setIsAuthenticated(true);
        setUserId('admin-user'); // 设置一个默认的管理员用户ID
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
    logout,
  };

  // 显示加载状态
  if (isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        <Spin size="large" />
        <div style={{ color: '#666' }}>正在初始化应用...</div>
      </div>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
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
