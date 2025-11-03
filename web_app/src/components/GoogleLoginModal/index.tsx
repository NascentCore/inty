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
 * - 弹窗内容目前仅包含 UI，不包含业务逻辑
 */

import { useModel } from '@umijs/max';
import { X } from 'lucide-react';
import './index.less';

const GoogleLoginModal: React.FC = () => {
  const { visible, hide } = useModel('googleLoginModal');

  // 点击遮罩层关闭弹窗
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      hide();
    }
  };

  if (!visible) {
    return null;
  }

  return (
    <div className="google-login-modal-backdrop" onClick={handleBackdropClick}>
      <div className="google-login-modal">
        {/* 关闭按钮 */}
        <button className="close-button" onClick={hide} aria-label="关闭">
          <X size={24} />
        </button>

        {/* 弹窗内容 */}
        <div className="modal-content">
          <h2 className="modal-title">Sign in to IntelliMate</h2>
          <p className="modal-description">
            Sign in with your Google account to access all features
          </p>

          {/* Google 登录按钮 */}
          <button className="google-login-button">
            <svg className="google-icon" viewBox="0 0 24 24" width="20" height="20">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            <span>Continue with Google</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default GoogleLoginModal;

