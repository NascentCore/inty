# Google Web Ads Demo

这是一个最简化的 Google Web Ads 集成演示，展示了如何在网页中集成 Google Ads 的转换跟踪和再营销标签。

## 功能特性

- ✅ Google Ads 全局站点标签 (gtag.js) 集成
- ✅ 转换事件跟踪
- ✅ 自定义事件跟踪
- ✅ 再营销标签（页面浏览自动跟踪）
- ✅ 简洁的演示界面

## 快速开始

### 1. 获取 Google Ads ID

1. 登录 [Google Ads](https://ads.google.com/)
2. 进入 **工具和设置** > **设置** > **账户设置**
3. 找到你的 **Google Ads ID**（格式：`AW-123456789`）

### 2. 创建转换操作

1. 在 Google Ads 中，进入 **工具和设置** > **转化**
2. 点击 **+** 创建新的转化操作
3. 选择 **网站** 作为转化来源
4. 选择转化类别（如：注册、购买、下载等）
5. 设置转化名称和值
6. 在安装步骤中，选择 **使用 Google 跟踪代码管理器或网站代码**
7. 复制生成的 **转化标签**（格式：`AbC-D_efG-Hijklmno`）

### 3. 配置代码

编辑 `index.html` 文件，替换以下内容：

1. **Google Ads ID**（两处）：
   ```javascript
   // 将 YOUR_GOOGLE_ADS_ID 替换为你的 ID
   'AW-YOUR_GOOGLE_ADS_ID'
   ```

2. **转化标签**：
   ```javascript
   // 将 YOUR_CONVERSION_LABEL 替换为你的转化标签
   trackConversion('YOUR_CONVERSION_LABEL', 1.0);
   ```

### 4. 运行 Demo

#### 方式一：直接打开 HTML 文件

在浏览器中直接打开 `index.html` 文件即可。

#### 方式二：使用本地服务器（推荐）

```bash
# 使用 Python 3
python3 -m http.server 8000

# 或使用 Node.js
npx http-server -p 8000
```

然后在浏览器中访问 `http://localhost:8000`

## 使用说明

1. **页面加载**：页面加载时会自动发送页面浏览事件，用于再营销
2. **表单提交**：填写表单并点击提交按钮，会触发转换事件
3. **查看日志**：打开浏览器开发者工具（F12），在控制台中可以看到发送的事件详情

## 代码说明

### Google Ads 全局站点标签

```html
<script async src="https://www.googletagmanager.com/gtag/js?id=AW-YOUR_GOOGLE_ADS_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'AW-YOUR_GOOGLE_ADS_ID');
</script>
```

### 转换跟踪

```javascript
gtag('event', 'conversion', {
    'send_to': 'AW-YOUR_GOOGLE_ADS_ID/YOUR_CONVERSION_LABEL',
    'value': 1.0,
    'currency': 'CNY'
});
```

### 自定义事件跟踪

```javascript
gtag('event', 'event_name', {
    'custom_parameter': 'value'
});
```

## 测试验证

### 1. Google Ads 转换跟踪测试

1. 在 Google Ads 中，进入 **工具和设置** > **转化**
2. 点击你的转化操作
3. 使用 **测试此转化操作** 功能
4. 在演示页面提交表单
5. 等待几分钟后查看是否记录到转换

### 2. 浏览器控制台检查

打开浏览器开发者工具（F12），在控制台中可以看到：
- 页面加载时的初始化日志
- 表单提交时的转换事件日志
- 自定义事件的详细信息

### 3. Google Tag Assistant（推荐）

1. 安装 [Google Tag Assistant Chrome 扩展](https://chrome.google.com/webstore/detail/tag-assistant-legacy-by-g/kejbdjndbnbjgmefkgdddjlbokphdefk)
2. 启用扩展后访问演示页面
3. 查看是否检测到 Google Ads 标签和转换事件

## 常见问题

### Q: 转换事件没有记录？

A: 检查以下几点：
- Google Ads ID 是否正确配置
- 转化标签是否正确
- 是否在测试模式下（测试模式下转换可能不会立即显示）
- 检查浏览器控制台是否有错误信息

### Q: 如何测试再营销标签？

A: 再营销标签会在页面加载时自动发送。可以在 Google Ads 中创建再营销受众，然后查看是否能够收集到访问者数据。

### Q: 如何在生产环境使用？

A: 
1. 确保所有配置正确
2. 在生产环境中替换占位符 ID 和标签
3. 使用 HTTPS 协议（Google Ads 要求）
4. 在生产环境中测试转换跟踪是否正常工作

## 进阶使用

### 多转化跟踪

如果需要跟踪多个转化操作，可以多次调用 `trackConversion`：

```javascript
trackConversion('CONVERSION_LABEL_1', 1.0);
trackConversion('CONVERSION_LABEL_2', 99.0);
```

### 动态转化值

根据实际业务设置转化值：

```javascript
const orderValue = 299.99;
trackConversion('YOUR_CONVERSION_LABEL', orderValue, 'CNY');
```

### 增强型转化

如果需要在转化事件中包含用户数据（如邮箱），可以使用增强型转化：

```javascript
gtag('event', 'conversion', {
    'send_to': 'AW-YOUR_GOOGLE_ADS_ID/YOUR_CONVERSION_LABEL',
    'value': 1.0,
    'currency': 'CNY',
    'user_data': {
        'email_address': 'user@example.com'
    }
});
```

## 参考文档

- [Google Ads 帮助中心 - 网站转化跟踪](https://support.google.com/google-ads/answer/1722022)
- [gtag.js 开发者指南](https://developers.google.com/analytics/devguides/collection/gtagjs)
- [Google Ads API 文档](https://developers.google.com/google-ads/api/docs/start)

## 注意事项

1. **隐私政策**：使用 Google Ads 跟踪需要在隐私政策中说明
2. **GDPR 合规**：如果在欧盟地区，需要获得用户同意
3. **测试环境**：建议先在测试环境中验证配置
4. **HTTPS**：生产环境必须使用 HTTPS 协议
