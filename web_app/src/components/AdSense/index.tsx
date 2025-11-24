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
  const insRef = useRef<HTMLDivElement>(null);
  const isInitialized = useRef<boolean>(false);
  const [isAvailable, setIsAvailable] = useState<boolean>(false);

  // 检查 AdSense 是否可用，并持续监听脚本加载
  useEffect(() => {
    // 立即检查一次
    if (isAdSenseAvailable()) {
      setIsAvailable(true);
      return;
    }

    // 如果不可用，等待脚本加载后重试
    let checkCount = 0;
    const maxChecks = 20; // 最多检查20次（10秒）
    const timer = setInterval(() => {
      checkCount++;
      const available = isAdSenseAvailable();
      if (available) {
        setIsAvailable(true);
        clearInterval(timer);
      } else if (checkCount >= maxChecks) {
        clearInterval(timer);
      }
    }, 500);

    return () => {
      clearInterval(timer);
    };
  }, []);

  // 初始化广告 - 确保在 DOM 元素准备好且脚本加载完成后执行
  useEffect(() => {
    // 如果不可用、已初始化或 DOM 元素未准备好，直接返回
    if (!isAvailable || isInitialized.current || !insRef.current) {
      return;
    }

    // 使用 requestAnimationFrame 确保 DOM 已完全渲染
    const initAd = () => {
      if (isInitialized.current || !insRef.current) {
        return;
      }

      try {
        // 确保 adsbygoogle 数组存在
        if (!(window as any).adsbygoogle) {
          (window as any).adsbygoogle = [];
        }

        // 初始化广告
        (window as any).adsbygoogle.push({});
        isInitialized.current = true;
      } catch (err) {
        console.error('AdSense 初始化失败:', err);
      }
    };

    // 延迟初始化，确保 DOM 完全准备好
    const timeoutId = setTimeout(() => {
      requestAnimationFrame(initAd);
    }, 100);

    return () => {
      clearTimeout(timeoutId);
    };
  }, [isAvailable]);

  // 开发环境：即使 AdSense 不可用，也显示占位符用于测试布局
  if (!isAvailable && ADSENSE_CONFIG.IS_DEV) {
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

  // 渲染广告 DOM 元素（生产环境即使脚本未加载也渲染，让 Google 可以检测到）
  return (
    <div ref={adRef} className={`adsense-container ${className || ''}`} style={style}>
      <ins
        ref={insRef as any}
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
