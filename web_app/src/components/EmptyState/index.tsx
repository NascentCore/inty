/**
 * EmptyState 空状态组件
 * 替代 Ant Design 的 Empty 组件
 */

import { Inbox } from 'lucide-react';
import React from 'react';
import Icon from '../Icon';
import './index.less';

/**
 * EmptyState 组件 Props
 */
interface IEmptyStateProps {
  /** 描述文本 */
  description?: string;
  /** 图标大小 */
  iconSize?: number;
  /** 自定义样式 */
  style?: React.CSSProperties;
}

/**
 * EmptyState 组件
 */
const EmptyState: React.FC<IEmptyStateProps> = ({
  description = 'No data',
  iconSize = 64,
  style,
}) => {
  return (
    <div className="empty-state" style={style}>
      <div className="empty-state-icon">
        <Icon icon={Inbox} size={iconSize} color="rgba(255, 255, 255, 0.4)" strokeWidth={1.5} />
      </div>
      <p className="empty-state-description">{description}</p>
    </div>
  );
};

export default EmptyState;
