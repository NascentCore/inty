// Google Web Ads 配置示例
// 将此文件重命名为 config.js 并在 index.html 中引入，或直接在 index.html 中配置

const GOOGLE_ADS_CONFIG = {
    // Google Ads ID（格式：AW-123456789）
    googleAdsId: 'AW-YOUR_GOOGLE_ADS_ID',
    
    // 转化标签配置
    conversions: {
        // 注册转化
        registration: {
            label: 'YOUR_REGISTRATION_CONVERSION_LABEL',
            value: 1.0,
            currency: 'CNY'
        },
        // 购买转化
        purchase: {
            label: 'YOUR_PURCHASE_CONVERSION_LABEL',
            value: 99.0,
            currency: 'CNY'
        },
        // 下载转化
        download: {
            label: 'YOUR_DOWNLOAD_CONVERSION_LABEL',
            value: 1.0,
            currency: 'CNY'
        }
    },
    
    // 是否启用调试模式
    debug: true,
    
    // 是否启用增强型转化
    enhancedConversions: false
};

// 使用示例
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GOOGLE_ADS_CONFIG;
}
