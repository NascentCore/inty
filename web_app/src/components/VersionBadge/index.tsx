/**
 * 版本号徽章组件
 *
 * 用途：在页面右下角显示半透明的构建日期版本号，用于开发测试
 * 使用示例：
 * ```tsx
 * <VersionBadge />
 * ```
 *
 * 注意事项：
 * - 版本号来自构建时注入的 BUILD_TIME 环境变量
 * - 固定在页面右下角，不影响其他内容
 * - 半透明样式，悬停显示详细信息
 */

import React, { useMemo } from 'react';
import './index.less';

/**
 * 版本号徽章组件
 */
const VersionBadge: React.FC = () => {
  /**
   * 格式化构建时间为易读格式
   */
  const formattedVersion = useMemo(() => {
    try {
      // BUILD_TIME 是在构建时通过 define 注入的全局变量
      const buildTime = typeof BUILD_TIME !== 'undefined' ? BUILD_TIME : new Date().toISOString();
      const date = new Date(buildTime);

      // 格式化为 YYYY-MM-DD HH:mm
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');

      return `${year}-${month}-${day} ${hours}:${minutes}`;
    } catch (error) {
      console.error('格式化构建时间失败:', error);
      return 'Invalid Build Time';
    }
  }, []);

  /**
   * 获取完整的 ISO 时间字符串（用于 title 提示）
   */
  const fullBuildTime = useMemo(() => {
    try {
      return typeof BUILD_TIME !== 'undefined' ? BUILD_TIME : new Date().toISOString();
    } catch {
      return '';
    }
  }, []);

  return (
    <div className="version-badge" title={`Build Time: ${fullBuildTime}`}>
      <span className="version-label">build</span>
      <span className="version-time">{formattedVersion}</span>
    </div>
  );
};

export default VersionBadge;

