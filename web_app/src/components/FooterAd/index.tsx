/**
 * 页脚广告组件
 * 
 * 用途：在页面底部显示横幅广告
 * 使用示例：
 * ```tsx
 * <FooterAd />
 * ```
 * 
 * Props 说明：
 * 无，组件内部自动使用配置的广告位 ID
 * 
 * 注意事项：
 * - 组件内部使用 AdSense 组件显示广告
 * - 广告位 ID 从 ADSENSE_CONFIG.AD_SLOTS.FOOTER 获取
 * - 开发环境会显示占位符用于测试布局
 */

import React from 'react';
import { AdSense } from '@/components';
import { ADSENSE_CONFIG } from '@/config/adsense';
import './index.less';

const FooterAd: React.FC = () => {
  return (
    <div className="footer-ad-wrapper">
      <AdSense
        adSlot={ADSENSE_CONFIG.AD_SLOTS.FOOTER}
        adFormat={ADSENSE_CONFIG.AD_FORMATS.AUTO}
        fullWidthResponsive={true}
        className="footer-ad"
      />
    </div>
  );
};

export default FooterAd;

