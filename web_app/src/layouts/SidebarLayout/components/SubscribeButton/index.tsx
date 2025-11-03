/**
 * 订阅按钮组件
 * 
 * 用途：通用的订阅按钮组件，支持独立和内联两种使用模式
 * 使用示例：
 * ```tsx
 * // 独立使用（带 wrapper）
 * <SubscribeButton onClick={handleSubscribe} />
 * 
 * // 内联使用（不带 wrapper，适合在 flex 布局中）
 * <SubscribeButton inline onClick={handleSubscribe} disabled={loading} />
 * ```
 * 
 * Props 说明：
 * - onClick: () => void - 按钮点击回调
 * - inline: boolean - 是否内联模式（默认 false，带 wrapper）
 * - disabled: boolean - 是否禁用（默认 false）
 */

import React from 'react';
import { Crown } from 'lucide-react';
import { Icon } from '@/components';
import './index.less';

interface ISubscribeButtonProps {
  /** 按钮点击回调 */
  onClick?: () => void;
  /** 是否内联模式（不带 wrapper） */
  inline?: boolean;
  /** 是否禁用 */
  disabled?: boolean;
}

/**
 * 订阅按钮
 */
const SubscribeButton: React.FC<ISubscribeButtonProps> = ({
  onClick,
  inline = false,
  disabled = false,
}) => {
  const buttonElement = (
    <button
      type="button"
      className={`subscribe-btn ${inline ? 'subscribe-btn-inline' : ''}`}
      onClick={onClick}
      disabled={disabled}
    >
      <span className="subscribe-icon">
        <Icon icon={Crown} size={16} color="#ffd700" />
      </span>
      <span className="subscribe-text">Subscribe</span>
    </button>
  );

  // 内联模式直接返回按钮，不带 wrapper
  if (inline) {
    return buttonElement;
  }

  // 独立模式带 wrapper
  return (
    <div className="subscribe-button-wrapper">{buttonElement}</div>
  );
};

export default SubscribeButton;

