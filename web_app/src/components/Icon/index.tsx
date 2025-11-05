/**
 * Icon 组件
 * 基于 Lucide Icons 的通用图标组件
 *
 * @example
 * ```tsx
 * import { Icon } from '@/components';
 * import { Send, Heart, Star } from 'lucide-react';
 *
 * // 基本用法
 * <Icon icon={Send} />
 *
 * // 自定义大小和颜色
 * <Icon icon={Heart} size={20} color="#ff4d4f" />
 *
 * // 添加点击事件
 * <Icon icon={Star} onClick={handleClick} className="clickable" />
 * ```
 *
 * 更多图标查看：https://lucide.dev/icons/
 */

import type { LucideIcon, LucideProps } from 'lucide-react';
import type React from 'react';
import './index.less';

interface IIconProps extends Omit<LucideProps, 'ref'> {
  /** Lucide 图标组件 */
  icon: LucideIcon;
  /** 自定义类名 */
  className?: string;
  /** 图标大小（像素） */
  size?: number;
  /** 图标颜色 */
  color?: string;
  /** 描边宽度 */
  strokeWidth?: number;
  /** 点击事件 */
  onClick?: () => void;
}

/**
 * Icon 组件
 * @param props - 组件属性
 */
const Icon: React.FC<IIconProps> = ({
  icon: LucideIcon,
  className = '',
  size = 24,
  color = 'rgba(255, 255, 255, 0.85)', // 深色主题默认浅色图标
  strokeWidth = 2,
  onClick,
  ...restProps
}) => {
  return (
    <span
      className={`icon-wrapper ${className}`}
      onClick={onClick}
      style={{
        width: size,
        height: size,
        color: color,
      }}
    >
      <LucideIcon size={size} strokeWidth={strokeWidth} {...restProps} />
    </span>
  );
};

export default Icon;
