/**
 * Google 登录弹窗组件
 *
 * 用途：全局 Google 登录弹窗，可通过 useModel('googleLoginModal') 控制显示/隐藏
 * 使用示例：
 * ```tsx
 * const { show } = useModel('googleLoginModal');
 * <button onClick={show}>打开登录弹窗</button>
 * ```
 *
 * 注意事项：
 * - 该组件已在 app.tsx 中全局引入，无需在页面中重复引入
 * - 登录成功后会自动更新全局用户状态并关闭弹窗
 */

import { GoogleLogin, GoogleOAuthProvider } from '@react-oauth/google';
import { history, useModel } from '@umijs/max';
import { X } from 'lucide-react';
import { useState } from 'react';
import { GOOGLE_AUTH_CONFIG } from '@/constants';
import { createIntyClient, logger, saveToken } from '@/utils';
import './index.less';

const GoogleLoginModal: React.FC = () => {
  const { visible, hide } = useModel('googleLoginModal');
  const { fetchUserProfile } = useModel('user');
  const { refreshChatList } = useModel('chatList');

  const [loginStatus, setLoginStatus] = useState<'idle' | 'loading' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');

  /**
   * 处理 Google 登录成功
   */
  const handleGoogleSuccess = async (credentialResponse: any) => {
    const idToken = credentialResponse.credential;

    if (!idToken) {
      setLoginStatus('error');
      setErrorMessage('Failed to get Google ID Token');
      return;
    }

    await loginWithIdToken(idToken);
  };

  /**
   * 处理 Google 登录失败
   */
  const handleGoogleError = () => {
    setLoginStatus('error');
    setErrorMessage('Google login failed, please try again');
    logger.error('Google login failed');
  };

  /**
   * 使用 ID Token 调用后端 API
   */
  const loginWithIdToken = async (idToken: string) => {
    setLoginStatus('loading');
    setErrorMessage('');

    try {
      const client = await createIntyClient();

      const response = await client.api.v1.auth.google.login({
        id_token: idToken,
        user_info: {
          system_language: navigator.language || 'en-US',
          age_group: '25-34',
          gender: 'OTHER',
        },
      });

      if (response.data?.token && response.data?.user) {
        // 保存 token
        await saveToken(response.data.token);

        // 获取用户详细信息
        await fetchUserProfile();

        // 刷新聊天列表
        await refreshChatList();

        // 重置状态并关闭弹窗
        setLoginStatus('idle');
        setErrorMessage('');
        hide();

        // 跳转到首页
        history.push('/');

        logger.info('Login successful', response.data.user);
      } else {
        throw new Error('Login response data is invalid');
      }
    } catch (err: unknown) {
      const error = err as { message?: string };
      setLoginStatus('error');
      setErrorMessage(error.message || 'Login failed, please try again');
      logger.error('Login failed', err);
    }
  };

  // 点击遮罩层关闭弹窗
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      handleClose();
    }
  };

  // 关闭弹窗并重置状态
  const handleClose = () => {
    hide();
    setLoginStatus('idle');
    setErrorMessage('');
  };

  if (!visible) {
    return null;
  }

  return (
    <GoogleOAuthProvider clientId={GOOGLE_AUTH_CONFIG.CLIENT_ID}>
      <div className="google-login-modal-backdrop" onClick={handleBackdropClick}>
        <div className="google-login-modal">
          {/* 关闭按钮 */}
          <button type="button" className="close-button" onClick={handleClose} aria-label="Close">
            <X size={24} />
          </button>

          {/* 弹窗内容 */}
          <div className="modal-content">
            <h2 className="modal-title">Sign in to IntelliMate</h2>
            <p className="modal-description">
              Sign in with your Google account to access all features
            </p>

            {/* Loading 状态 */}
            {loginStatus === 'loading' && (
              <div className="login-loading">
                <div className="spinner" />
                <p>Signing in...</p>
              </div>
            )}

            {/* Error 状态 */}
            {loginStatus === 'error' && (
              <div className="login-error">
                <p>{errorMessage}</p>
              </div>
            )}

            {/* Google 登录按钮 */}
            {loginStatus !== 'loading' && (
              <div className="google-login-wrapper">
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={handleGoogleError}
                  theme="outline"
                  size="large"
                  text="continue_with"
                  shape="rectangular"
                  width="100%"
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </GoogleOAuthProvider>
  );
};

export default GoogleLoginModal;
