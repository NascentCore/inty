/**
 * Loading 加载组件
 *
 * 用途：显示加载状态，使用 SpinKit 三点弹跳动画
 * 使用示例：
 * ```tsx
 * <Loading size="small" />
 * <Loading size="default" tip="加载中..." />
 * <Loading size="large" fullscreen />
 * ```
 *
 * Props 说明：
 * - tip: string - 加载提示文本（可选）
 * - size: 'small' | 'default' | 'large' - 尺寸大小，默认 'default'
 * - fullscreen: boolean - 是否全屏居中显示，默认 false
 */

import React from 'react';
import './index.less';

/**
 * Loading 组件 Props
 */
interface ILoadingProps {
  /** 加载提示文本 */
  tip?: string;
  /** 尺寸 */
  size?: 'small' | 'default' | 'large';
  /** 是否全屏居中 */
  fullscreen?: boolean;
}

/**
 * Loading 组件
 */
const Loading: React.FC<ILoadingProps> = ({ tip, size = 'default', fullscreen = false }) => {
  const sizeClass = `loading-${size}`;
  const containerClass = fullscreen ? 'loading-container fullscreen' : 'loading-container';

  return (
    <div className={containerClass}>
      <div className={`loading-spinner ${sizeClass}`}>
        <div className="bounce1" />
        <div className="bounce2" />
        <div className="bounce3" />
      </div>
      {tip && <p className="loading-tip">{tip}</p>}
    </div>
  );
};

export default Loading;
