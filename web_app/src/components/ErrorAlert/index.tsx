/**
 * ErrorAlert 错误提示组件
 * 替代 Ant Design 的 Alert 组件
 */

import React, { useState } from 'react';
import { XCircle, AlertTriangle, Info, CheckCircle, X } from 'lucide-react';
import Icon from '../Icon';
import './index.less';

/**
 * ErrorAlert 组件 Props
 */
interface IErrorAlertProps {
  /** 错误标题 */
  message?: string;
  /** 错误描述 */
  description?: string;
  /** 是否可关闭 */
  closable?: boolean;
  /** 关闭回调 */
  onClose?: () => void;
  /** 类型 */
  type?: 'error' | 'warning' | 'info' | 'success';
}

/**
 * ErrorAlert 组件
 */
const ErrorAlert: React.FC<IErrorAlertProps> = ({
  message = 'Error',
  description,
  closable = false,
  onClose,
  type = 'error',
}) => {
  const [visible, setVisible] = useState(true);

  const handleClose = () => {
    setVisible(false);
    onClose?.();
  };

  if (!visible) {
    return null;
  }

  const getIcon = () => {
    const iconColor = '#333333'; // Alert 组件使用深色图标（因为背景是浅色）
    switch (type) {
      case 'error':
        return <Icon icon={XCircle} size={20} color={iconColor} />;
      case 'warning':
        return <Icon icon={AlertTriangle} size={20} color={iconColor} />;
      case 'info':
        return <Icon icon={Info} size={20} color={iconColor} />;
      case 'success':
        return <Icon icon={CheckCircle} size={20} color={iconColor} />;
      default:
        return <Icon icon={XCircle} size={20} color={iconColor} />;
    }
  };

  return (
    <div className={`error-alert alert-${type}`}>
      <div className="error-alert-icon">{getIcon()}</div>
      <div className="error-alert-content">
        <div className="error-alert-message">{message}</div>
        {description && <div className="error-alert-description">{description}</div>}
      </div>
      {closable && (
        <button className="error-alert-close" onClick={handleClose} type="button">
          <Icon icon={X} size={16} color="#999999" />
        </button>
      )}
    </div>
  );
};

export default ErrorAlert;

