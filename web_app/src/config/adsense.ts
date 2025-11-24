// Google AdSense 配置
export const ADSENSE_CONFIG = {
  // 广告位配置
  AD_SLOTS: {
    // 页面顶部横幅广告
    TOP_BANNER: process.env.REACT_APP_ADSENSE_SLOT_TOP_BANNER || '4154399825',

    // 页脚广告（页面底部广告）
    FOOTER: process.env.REACT_APP_ADSENSE_SLOT_FOOTER || '8033224641',
  },

  // 广告格式
  AD_FORMATS: {
    AUTO: 'auto',
    RECTANGLE: 'rectangle',
    HORIZONTAL: 'horizontal',
    VERTICAL: 'vertical',
  },

  // 是否为开发环境（通过域名判断，localhost 为开发环境）
  IS_DEV:
    typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1' ||
      window.location.hostname === '[::1]'),
};

// 检查 AdSense 是否可用
export const isAdSenseAvailable = (): boolean => {
  return typeof window !== 'undefined' && !!(window as any).adsbygoogle;
};
