/**
 * Google AdSense 广告组件
 *
 * 用途：在页面中显示 Google AdSense 广告
 * 使用示例：
 * ```tsx
 * <AdSense
 *   adSlot="1234567890"
 *   adFormat="auto"
 *   fullWidthResponsive={true}
 * />
 * ```
 *
 * Props 说明：
 * - adSlot: string - 广告位 ID（必需）
 * - adFormat: string - 广告格式，如 'auto', 'rectangle', 'horizontal' 等（可选，默认 'auto'）
 * - fullWidthResponsive: boolean - 是否全宽响应式（可选，默认 true）
 * - style: React.CSSProperties - 自定义样式（可选）
 * - className: string - 自定义类名（可选）
 *
 * 注意事项：
 * - 需要先在 config/config.ts 中配置 AdSense 脚本
 * - 广告位 ID 需要在 Google AdSense 后台创建广告单元后获取
 * - 组件会在挂载后自动初始化广告
 * - 组件内部会自动检查 AdSense 是否可用，不可用时不会渲染
 */

import React, { useEffect, useRef, useState } from 'react';
import { ADSENSE_CONFIG } from '@/config/adsense';
import './index.less';

interface IAdSenseProps {
  /** 广告位 ID（必需） */
  adSlot: string;
  /** 广告格式，如 'auto', 'rectangle', 'horizontal' 等 */
  adFormat?: string;
  /** 是否全宽响应式 */
  fullWidthResponsive?: boolean;
  /** 自定义样式 */
  style?: React.CSSProperties;
  /** 自定义类名 */
  className?: string;
}

/**
 * 检查 AdSense 是否可用
 * 内部使用，不对外导出
 */
const isAdSenseAvailable = (): boolean => {
  return typeof window !== 'undefined' && !!(window as any).adsbygoogle;
};

const AdSense: React.FC<IAdSenseProps> = ({
  adSlot,
  adFormat = 'auto',
  fullWidthResponsive = true,
  style,
  className,
}) => {
  const adRef = useRef<HTMLDivElement>(null);
  const isInitialized = useRef<boolean>(false);
  const [isAvailable, setIsAvailable] = useState<boolean>(false);

  // 检查 AdSense 是否可用
  useEffect(() => {
    const checkAvailability = () => {
      const available = isAdSenseAvailable();
      setIsAvailable(available);
      return available;
    };

    // 立即检查一次
    if (checkAvailability()) {
      return;
    }

    // 如果不可用，等待脚本加载后重试
    const timer = setInterval(() => {
      if (checkAvailability()) {
        clearInterval(timer);
      }
    }, 500);

    // 设置最大等待时间（5秒）
    const maxWaitTimer = setTimeout(() => {
      clearInterval(timer);
    }, 5000);

    return () => {
      clearInterval(timer);
      clearTimeout(maxWaitTimer);
    };
  }, []);

  // 初始化广告
  useEffect(() => {
    // 如果不可用或已初始化，直接返回
    if (!isAvailable || isInitialized.current || !adRef.current) {
      return;
    }

    try {
      // 初始化广告
      if (!(window as any).adsbygoogle) {
        (window as any).adsbygoogle = [];
      }
      (window as any).adsbygoogle.push({});
      isInitialized.current = true;
    } catch (err) {
      console.error('AdSense 初始化失败:', err);
    }
  }, [isAvailable]);

  // 开发环境：即使 AdSense 不可用，也显示占位符用于测试布局
  if (!isAvailable) {
    if (ADSENSE_CONFIG.IS_DEV) {
      return (
        <div className={`adsense-container adsense-placeholder ${className || ''}`} style={style}>
          <div className="adsense-placeholder-content">
            <span className="adsense-placeholder-text">AdSense 占位符</span>
            <span className="adsense-placeholder-info">广告位 ID: {adSlot} | 格式: {adFormat}</span>
            <span className="adsense-placeholder-tip">(本地测试模式 - 实际广告仅在生产环境显示)</span>
          </div>
        </div>
      );
    }
    return null;
  }

  return (
    <div ref={adRef} className={`adsense-container ${className || ''}`} style={style}>
      <ins
        className="adsbygoogle"
        data-ad-client="ca-pub-2092760210658178"
        data-ad-slot={adSlot}
        data-ad-format={adFormat}
        data-full-width-responsive={fullWidthResponsive ? 'true' : 'false'}
      />
    </div>
  );
};

export default AdSense;
