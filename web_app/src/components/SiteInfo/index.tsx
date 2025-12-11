/**
 * SiteInfo 站点信息组件
 *
 * 用途：展示产品品牌标识（图标与名称）。
 * 使用示例：
 * ```tsx
 * <SiteInfo />
 * ```
 *
 * Props 说明：
 * - className: string | undefined - 额外的容器 class
 *
 * 注意事项：
 * - 默认包含点击手势样式；如需禁用可自行覆盖样式。
 */
import React from 'react';
import { Sparkles } from 'lucide-react';
import { Icon } from '@/components';
import './index.less';

interface ISiteInfoProps {
  className?: string;
}

const SiteInfo: React.FC<ISiteInfoProps> = ({ className }) => {
  const containerClassName = className ? `site-info-block ${className}` : 'site-info-block';

  return (
    <div className={containerClassName}>
      <div className="site-info-logo">
        <Icon icon={Sparkles} size={28} />
      </div>
      <h1 className="site-info-name">IntelliMate</h1>
    </div>
  );
};

export default SiteInfo;
