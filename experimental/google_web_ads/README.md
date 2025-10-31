# Google Web Ads Demo

最简化的 Google Web Ads 集成演示，展示如何在网页中集成 Google Ads 的转换跟踪和再营销标签。

## 核心功能

- ✅ Google Ads 全局站点标签 (gtag.js) 集成
- ✅ 转换事件跟踪
- ✅ 页面浏览自动跟踪（用于再营销）

## 快速开始

### 1. 获取 Google Ads ID

1. 登录 [Google Ads](https://ads.google.com/)
2. 进入 **工具和设置** > **设置** > **账户设置**
3. 复制你的 **Google Ads ID**（格式：`AW-123456789`）

### 2. 创建转化操作

1. 在 Google Ads 中，进入 **工具和设置** > **转化**
2. 点击 **+** 创建新的转化操作
3. 选择 **网站** 作为转化来源
4. 选择转化类别（如：注册、购买等）
5. 在安装步骤中，选择 **使用 Google 跟踪代码管理器或网站代码**
6. 复制生成的 **转化标签**（格式：`AbC-D_efG-Hijklmno`）

### 3. 配置代码

编辑 `index.html`，替换以下两处：

**位置 1：第 135 和 140 行** - 替换 Google Ads ID
```javascript
// 第 135 行：script src 中的 ID
<script async src="...gtag/js?id=AW-YOUR_GOOGLE_ADS_ID"></script>

// 第 140 行：配置变量
const GOOGLE_ADS_ID = 'AW-YOUR_GOOGLE_ADS_ID';
```

**位置 2：第 141 行** - 替换转化标签
```javascript
const CONVERSION_LABEL = 'YOUR_CONVERSION_LABEL';
```

### 4. 运行 Demo

```bash
# 使用 Python 3
python3 -m http.server 8000

# 或直接打开 index.html
```

访问 `http://localhost:8000`，填写表单并提交，查看浏览器控制台（F12）的事件日志。

## Google Web Ads 集成代码说明

### 核心代码结构

```html
<!-- 1. 加载 gtag.js -->
<script async src="https://www.googletagmanager.com/gtag/js?id=AW-YOUR_GOOGLE_ADS_ID"></script>

<script>
  // 2. 初始化
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  
  // 3. 配置 Google Ads ID（自动发送页面浏览）
  gtag('config', 'AW-YOUR_GOOGLE_ADS_ID', {
    'send_page_view': true
  });
  
  // 4. 转换跟踪函数
  function trackConversion(conversionLabel, value, currency = 'CNY') {
    gtag('event', 'conversion', {
      'send_to': 'AW-YOUR_GOOGLE_ADS_ID/' + conversionLabel,
      'value': value,
      'currency': currency
    });
  }
</script>
```

### 触发转换事件

在需要跟踪转换的地方调用：

```javascript
trackConversion('YOUR_CONVERSION_LABEL', 1.0);
```

## 验证安装

1. **浏览器控制台**：打开开发者工具（F12），提交表单后应看到转换事件日志
2. **Google Tag Assistant**：安装 [Chrome 扩展](https://chrome.google.com/webstore/detail/tag-assistant-legacy-by-g/kejbdjndbnbjgmefkgdddjlbokphdefk)，检查是否检测到 Google Ads 标签
3. **Google Ads 后台**：进入 **工具和设置** > **转化**，使用"测试此转化操作"功能验证

## 常见问题

**Q: 转换事件没有记录？**

A: 检查：
- Google Ads ID 和转化标签是否正确配置
- 浏览器是否阻止了第三方 Cookie
- 是否使用了广告拦截器

**Q: 如何测试再营销标签？**

A: 再营销标签会在页面加载时自动发送。`gtag('config')` 中的 `send_page_view: true` 已启用此功能。

## 参考文档

- [Google Ads 网站转化跟踪](https://support.google.com/google-ads/answer/1722022)
- [gtag.js 开发者指南](https://developers.google.com/analytics/devguides/collection/gtagjs)

## 注意事项

- 生产环境必须使用 HTTPS 协议
- 建议在隐私政策中说明使用 Google Ads 跟踪
- 转化数据可能有延迟（几小时到一天）
