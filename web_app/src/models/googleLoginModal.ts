/**
 * Google 登录弹窗状态管理
 * 
 * 提供全局的 Google 登录弹窗显示/隐藏控制
 */

import { useState } from 'react';

export interface IGoogleLoginModalState {
  /** 弹窗是否可见 */
  visible: boolean;
  /** 显示弹窗 */
  show: () => void;
  /** 隐藏弹窗 */
  hide: () => void;
}

export default function useGoogleLoginModal(): IGoogleLoginModalState {
  const [visible, setVisible] = useState(false);

  const show = () => {
    setVisible(true);
  };

  const hide = () => {
    setVisible(false);
  };

  return {
    visible,
    show,
    hide,
  };
}

