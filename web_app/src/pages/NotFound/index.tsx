import { useNavigate } from '@umijs/max';
import React from 'react';
import './index.less';

/**
 * 404 页面 - 使用原生 HTML + Less 实现
 */
const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  const handleBackHome = () => {
    navigate('/');
  };

  return (
    <div className="not-found-page">
      <div className="not-found-container">
        <div className="not-found-icon">404</div>
        <h1 className="not-found-title">页面未找到</h1>
        <p className="not-found-subtitle">抱歉，您访问的页面不存在。</p>
        <button type="button" className="not-found-button" onClick={handleBackHome}>
          返回首页
        </button>
      </div>
    </div>
  );
};

export default NotFoundPage;
