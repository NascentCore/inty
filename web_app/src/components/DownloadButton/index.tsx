/**
 * DownloadButton 下载按钮
 *
 * 用途：展示 Google Play 下载入口
 * 使用示例：
 * ```tsx
 * <DownloadButton />
 * <DownloadButton onClick={customHandler} />
 * ```
 *
 * Props 说明：
 * - onClick?: () => void - 自定义点击处理
 *
 * 注意事项：
 * - 默认跳转到 Google Play，传入 onClick 时需要自行处理跳转
 * - CREATED_BY_AGENT
 */

import React, { useCallback } from 'react';
import './index.less';

export interface IDownloadButtonProps {
  onClick?: () => void;
}

const GOOGLE_PLAY_URL = 'https://play.google.com/store/apps/details?id=com.ai.intellimate';

const DownloadButton: React.FC<IDownloadButtonProps> = ({ onClick }) => {
  const handleClick = useCallback(() => {
    if (onClick) {
      onClick();
      return;
    }
    window.open(GOOGLE_PLAY_URL, '_blank');
  }, [onClick]);

  return (
    <button type="button" className="sidebar-download-button" onClick={handleClick}>
      <img
        src="https://upload.wikimedia.org/wikipedia/commons/7/78/Google_Play_Store_badge_EN.svg"
        alt="Get it on Google Play"
        loading="lazy"
      />
    </button>
  );
};

export default DownloadButton;
