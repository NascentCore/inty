/**
 * Discover 按钮组件
 */

import React from 'react';
import { Compass } from 'lucide-react';
import { Icon } from '@/components';
import './index.less';

interface IDiscoverButtonProps {
  onClick?: () => void;
}

/**
 * Discover 按钮
 */
const DiscoverButton: React.FC<IDiscoverButtonProps> = ({ onClick }) => {
  return (
    <div className="discover-button-wrapper">
      <button type="button" className="discover-btn" onClick={onClick}>
        <span className="discover-icon">
          <Icon icon={Compass} size={18} />
        </span>
        <span className="discover-text">Discover</span>
      </button>
    </div>
  );
};

export default DiscoverButton;

