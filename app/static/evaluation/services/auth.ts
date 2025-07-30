/**
 * 认证管理服务
 * 用于评测系统的用户认证和token管理
 */

interface GuestUser {
  guest_id: string;
  token: string;
  is_new_guest: boolean;
}

interface AuthResponse {
  code: number;
  message: string;
  data: GuestUser;
}

class AuthService {
  private static instance: AuthService;
  private baseURL: string;
  
  constructor(baseURL: string = '/api') {
    this.baseURL = baseURL;
  }

  static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  /**
   * 获取当前存储的token
   */
  getToken(): string | null {
    return localStorage.getItem('auth_token');
  }

  /**
   * 获取当前用户ID
   */
  getUserId(): string | null {
    return localStorage.getItem('user_id');
  }

  /**
   * 保存认证信息
   */
  private saveAuth(token: string, userId: string): void {
    localStorage.setItem('auth_token', token);
    localStorage.setItem('user_id', userId);
  }

  /**
   * 清除认证信息
   */
  clearAuth(): void {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_id');
  }

  /**
   * 检查是否已认证
   */
  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  /**
   * 创建游客用户并获取token
   */
  async createGuestUser(): Promise<{ success: boolean; token?: string; userId?: string; error?: string }> {
    try {
      // 生成一个简单的设备ID
      const deviceId = this.generateDeviceId();
      
      const response = await fetch(`${this.baseURL}/v1/auth/guest`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          device_id: deviceId,
          system_language: 'zh-CN',
          age_group: 'adult'
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result: AuthResponse = await response.json();
      
      if (result.code === 200 && result.data) {
        const { token, guest_id } = result.data;
        this.saveAuth(token, guest_id);
        
        console.log('🎉 游客用户创建成功:', guest_id);
        
        return {
          success: true,
          token,
          userId: guest_id
        };
      } else {
        throw new Error(result.message || '创建游客用户失败');
      }
    } catch (error) {
      console.error('创建游客用户失败:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      };
    }
  }

  /**
   * 自动认证 - 如果没有token则创建游客用户
   */
  async ensureAuthenticated(): Promise<boolean> {
    if (this.isAuthenticated()) {
      return true;
    }

    console.log('🔐 未找到认证token，创建游客用户...');
    const result = await this.createGuestUser();
    
    if (result.success) {
      console.log('✅ 自动认证成功');
      return true;
    } else {
      console.error('❌ 自动认证失败:', result.error);
      return false;
    }
  }

  /**
   * 生成设备ID
   */
  private generateDeviceId(): string {
    // 尝试从localStorage获取已存储的设备ID
    let deviceId = localStorage.getItem('device_id');
    
    if (!deviceId) {
      // 生成新的设备ID
      deviceId = 'eval-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('device_id', deviceId);
    }
    
    return deviceId;
  }

  /**
   * 获取认证头部
   */
  getAuthHeaders(): Record<string, string> {
    const token = this.getToken();
    if (token) {
      return {
        'Authorization': `Bearer ${token}`
      };
    }
    return {};
  }
}

// 导出单例实例
export const authService = AuthService.getInstance();
export default authService;