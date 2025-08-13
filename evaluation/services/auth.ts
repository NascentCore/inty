/**
 * 认证管理服务
 * 用于评测系统的用户认证和token管理
 * 注意：token 已硬编码在API客户端中，此服务仅用于兼容性
 * TODO: 删除此文件
 */

class AuthService {
  private static instance: AuthService;

  constructor() {
    // 空构造函数
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
   * 由于token已硬编码，始终返回true
   */
  isAuthenticated(): boolean {
    return true;
  }

  /**
   * 自动认证 - 由于token已硬编码，始终返回true
   */
  async ensureAuthenticated(): Promise<boolean> {
    console.log('✅ 使用硬编码token，无需认证');
    return true;
  }

  /**
   * 获取认证头部
   */
  getAuthHeaders(): Record<string, string> {
    const token = this.getToken();
    if (token) {
      return {
        Authorization: `Bearer ${token}`,
      };
    }
    return {};
  }
}

// 导出单例实例
export const authService = AuthService.getInstance();
export default authService;
