# Android Firebase 远程日志采集示例 - 日志采集

这是一个基于 Firebase 的 Android 远程日志采集示例应用，展示如何集成 Firebase Analytics 和 Crashlytics 来收集应用日志和崩溃信息。

## 功能特性

- Firebase Analytics 集成
- Firebase Crashlytics 集成
- 自定义日志事件记录
- 崩溃报告自动收集
- 用户行为追踪
- 性能监控

## Firebase 配置要求

### 1. 创建 Firebase 项目

1. 访问 [Firebase Console](https://console.firebase.google.com/)
2. 创建新项目或选择现有项目
3. 在项目设置中启用以下服务：
   - Firebase Analytics
   - Firebase Crashlytics

### 2. 添加 Android 应用

1. 在 Firebase 项目中点击"添加应用" → "Android"
2. 输入包名：`com.example.firebaselogging`
3. 下载 `google-services.json` 文件
4. 将文件放置在 `app/` 目录下

### 3. 获取必要的配置信息

#### google-services.json 文件
这是最重要的配置文件，包含：
- `project_id`: Firebase 项目 ID
- `client_id`: OAuth 客户端 ID
- `api_key`: Web API 密钥
- `app_id`: 应用 ID
- `storage_bucket`: 存储桶名称

#### Firebase 项目设置中的信息
- **项目 ID**: 在项目概览页面可以找到
- **Web API 密钥**: 在项目设置 → 常规 → Web API 密钥
- **服务账号密钥**: 在项目设置 → 服务账号 → 生成新的私钥

### 4. 配置步骤

1. **下载 google-services.json**
   ```bash
   # 将下载的 google-services.json 文件放在以下位置：
   app/google-services.json
   ```

2. **配置 Firebase 服务**
   - 在 Firebase Console 中启用 Analytics
   - 在 Firebase Console 中启用 Crashlytics
   - 确保应用已正确注册

3. **测试配置**
   - 运行应用
   - 查看 Firebase Console 中的 Analytics 和 Crashlytics 数据
   - 触发测试崩溃以验证 Crashlytics 工作正常

## 项目结构

```
android_firebase_logging/
├── app/
│   ├── build.gradle.kts
│   ├── google-services.json          # Firebase 配置文件（需要从 Firebase Console 下载）
│   └── src/
│       └── main/
│           ├── AndroidManifest.xml
│           └── java/com/example/firebaselogging/
│               ├── MainActivity.kt
│               ├── LoggingManager.kt
│               └── LogEvent.kt
├── build.gradle.kts
├── settings.gradle.kts
└── README.md
```

## 使用方法

1. 按照上述步骤配置 Firebase
2. 下载 `google-services.json` 文件到 `app/` 目录
3. 使用 Android Studio 打开项目
4. 同步 Gradle 文件
5. 运行应用

## 主要功能

### 日志记录
- 用户行为事件
- 自定义事件参数
- 错误日志记录

### 崩溃报告
- 自动崩溃检测
- 崩溃堆栈信息
- 用户会话信息

### 性能监控
- 应用启动时间
- 网络请求性能
- 用户交互响应时间

## 注意事项

- 确保 `google-services.json` 文件包含正确的包名
- 在生产环境中注意用户隐私和数据保护
- 定期检查 Firebase 配额和计费
- 考虑日志数据的保留策略

## 故障排除

### 常见问题

1. **应用无法连接到 Firebase**
   - 检查 `google-services.json` 文件是否正确放置
   - 确认包名是否匹配
   - 检查网络连接

2. **Analytics 数据不显示**
   - 等待 24-48 小时（数据有延迟）
   - 检查 Firebase Console 中的实时事件
   - 确认 Analytics 已启用

3. **Crashlytics 不工作**
   - 确保已添加 Crashlytics 依赖
   - 检查 `google-services.json` 中的 Crashlytics 配置
   - 运行测试崩溃验证

## 相关文档

- [Firebase Android 设置指南](https://firebase.google.com/docs/android/setup)
- [Firebase Analytics 文档](https://firebase.google.com/docs/analytics)
- [Firebase Crashlytics 文档](https://firebase.google.com/docs/crashlytics)