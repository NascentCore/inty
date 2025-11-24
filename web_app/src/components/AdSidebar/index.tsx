/**
 * AdSidebar
 *
 * 用途：在侧边栏展示 Google AdSense 广告
 * 使用示例：
 * ```tsx
 * <AdSidebar />
 * ```
 *
 * Props 说明：
 * - 无额外 props，组件内部负责渲染广告位
 *
 * 注意事项：
 * - 依赖于外部已经在 `<head>` 中注入的 AdSense 脚本
 * - 组件挂载时自动触发 `adsbygoogle.push({})`
 */

import React, { useEffect, useRef } from 'react';
import { logger } from '@/utils/logger';
import './index.less';

const ADS_CLIENT_ID = 'ca-pub-2092760210658178';
const ADS_SLOT_ID = '4336139323';

interface IAdsWindow extends Window {
  adsbygoogle?: Array<Record<string, unknown>>;
}

const AdSidebar: React.FC = () => {
  const adRef = useRef<HTMLModElement | null>(null);

  useEffect(() => {
    if (!adRef.current) {
      logger.error('AdSidebar: adRef is not found');
      return;
    }

    try {
      const adsWindow = window as IAdsWindow;
      adsWindow.adsbygoogle = adsWindow.adsbygoogle ?? [];
      adsWindow.adsbygoogle.push({});
    } catch (err: unknown) {
      logger.error('AdSidebar: failed to push ads config', err);
    }
  }, []);

  return (
    <div className="ad-sidebar-wrapper">
      <ins
        className="adsbygoogle"
        style={{ display: 'block' }}
        data-ad-format="autorelaxed"
        data-ad-client={ADS_CLIENT_ID}
        data-ad-slot={ADS_SLOT_ID}
        ref={adRef}
      />
    </div>
  );
};

export default AdSidebar;
