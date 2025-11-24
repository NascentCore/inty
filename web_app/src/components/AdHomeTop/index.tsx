/**
 * AdHomeTop
 *
 * 用途：在首页上方展示 Google AdSense 横向广告
 * 使用示例：
 * ```tsx
 * <AdHomeTop />
 * ```
 *
 * Props 说明：
 * - 无额外 props，组件内部负责渲染广告位
 *
 * 注意事项：
 * - 依赖 `<head>` 中已注入的 AdSense 脚本
 * - 挂载时自动执行 `adsbygoogle.push({})`
 */

import React, { useEffect, useRef } from 'react';
import { logger } from '@/utils/logger';
import './index.less';

const ADS_CLIENT_ID = 'ca-pub-2092760210658178';
const ADS_SLOT_ID = '9913282523';

interface IAdsWindow extends Window {
  adsbygoogle?: Array<Record<string, unknown>>;
}

const AdHomeTop: React.FC = () => {
  const adRef = useRef<HTMLModElement | null>(null);

  useEffect(() => {
    if (!adRef.current) {
      logger.error('AdHomeTop: adRef is not found');
      return;
    }

    try {
      const adsWindow = window as IAdsWindow;
      adsWindow.adsbygoogle = adsWindow.adsbygoogle ?? [];
      adsWindow.adsbygoogle.push({});
    } catch (err: unknown) {
      logger.error('AdHomeTop: failed to push ads config', err);
    }
  }, []);

  return (
    <div className="ad-home-top-wrapper">
      {/* 首页上方 横向广告 */}
      <ins
        className="adsbygoogle"
        style={{ display: 'block' }}
        data-ad-client={ADS_CLIENT_ID}
        data-ad-slot={ADS_SLOT_ID}
        data-ad-format="auto"
        data-full-width-responsive="true"
        ref={adRef}
      />
    </div>
  );
};

export default AdHomeTop;

