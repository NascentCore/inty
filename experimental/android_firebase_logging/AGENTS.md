# Android Firebase 日志采集示例

## 项目概述

这是一个基于 Firebase 的 Android 远程日志采集示例应用，展示如何集成 Firebase Analytics、Crashlytics 和 Performance Monitoring 来收集应用日志和崩溃信息。

## 技术栈

- **语言**: Kotlin
- **构建工具**: Gradle (Kotlin DSL)
- **UI框架**: Android Views + Material Design
- **Firebase服务**: Analytics, Crashlytics, Performance Monitoring
- **最低SDK**: API 24 (Android 7.0)
- **目标SDK**: API 34 (Android 14)

## 项目结构

```
android_firebase_logging/
├── app/
│   ├── build.gradle.kts              # 应用级构建配置
│   ├── google-services.json          # Firebase 配置文件（需要从 Firebase Console 下载）
│   ├── google-services.json.example  # Firebase 配置文件示例
│   ├── proguard-rules.pro            # ProGuard 混淆规则
│   └── src/main/
│       ├── AndroidManifest.xml       # 应用清单文件
│       ├── java/com/example/firebaselogging/
│       │   ├── MainActivity.kt       # 主 Activity
│       │   ├── LoggingManager.kt     # 日志管理类
│       │   └── LogEvent.kt           # 日志事件数据类
│       └── res/
│           ├── layout/
│           │   └── activity_main.xml # 主界面布局
│           ├── values/
│           │   ├── strings.xml       # 字符串资源
│           │   └── themes.xml        # 主题样式
│           └── xml/
│               ├── backup_rules.xml      # 备份规则
│               └── data_extraction_rules.xml # 数据提取规则
├── build.gradle.kts                  # 项目级构建配置
├── settings.gradle.kts               # Gradle 设置
├── README.md                         # 项目说明文档
├── FIREBASE_SETUP_GUIDE.md          # Firebase 配置指南
└── AGENTS.md                         # 本文件
```

## 核心功能

### 1. Firebase Analytics 集成
- 自动事件记录（应用启动、暂停、恢复）
- 自定义事件记录
- 用户属性设置
- 用户ID管理

### 2. Firebase Crashlytics 集成
- 自动崩溃检测和报告
- 自定义错误日志记录
- 用户会话信息收集
- 自定义键值对设置

### 3. Firebase Performance Monitoring
- 自定义性能跟踪
- 应用启动时间监控
- 网络请求性能监控
- 用户交互响应时间监控

### 4. 日志管理
- 统一的日志记录接口
- 实时日志输出显示
- 错误处理和异常捕获
- 日志格式化和时间戳

## 主要类说明

### LoggingManager
- **职责**: 统一管理所有 Firebase 服务
- **功能**: 
  - 事件记录
  - 用户属性设置
  - 崩溃报告
  - 性能监控
  - 日志输出管理

### LogEvent
- **职责**: 定义日志事件的数据结构
- **功能**:
  - 预定义事件名称
  - 预定义参数键
  - 事件数据封装

### MainActivity
- **职责**: 用户界面和交互处理
- **功能**:
  - 按钮点击处理
  - 日志输出显示
  - 用户输入处理
  - 生命周期管理

## Firebase 配置要求

### 必需信息
1. **google-services.json 文件**
   - 从 Firebase Console 下载
   - 包含项目ID、API密钥、应用ID等
   - 必须放置在 `app/` 目录下

2. **Firebase 项目设置**
   - 项目ID
   - Web API 密钥
   - 服务账号密钥（可选）

### 必需服务
- Firebase Analytics
- Firebase Crashlytics
- Firebase Performance Monitoring

## 使用方法

### 1. 配置 Firebase
1. 按照 `FIREBASE_SETUP_GUIDE.md` 创建 Firebase 项目
2. 下载 `google-services.json` 文件到 `app/` 目录
3. 启用所需 Firebase 服务

### 2. 构建和运行
1. 使用 Android Studio 打开项目
2. 同步 Gradle 文件
3. 构建并运行应用

### 3. 测试功能
1. 点击各种按钮测试不同功能
2. 查看应用内的日志输出
3. 在 Firebase Console 中查看数据

## 开发注意事项

### 代码规范
- 使用 Kotlin 语言
- 遵循 Android 开发最佳实践
- 使用 Material Design 组件
- 实现适当的错误处理

### 安全考虑
- 不要将 `google-services.json` 提交到公共仓库
- 在生产环境中使用不同的 Firebase 项目
- 注意用户隐私和数据保护

### 性能优化
- 使用单例模式管理 LoggingManager
- 避免在主线程执行耗时操作
- 合理使用 Firebase 配额

## 扩展功能

### 可添加的功能
1. Firebase Remote Config 集成
2. Firebase A/B Testing
3. Firebase Cloud Messaging
4. 自定义崩溃报告界面
5. 日志导出功能
6. 离线日志缓存

### 自定义配置
1. 修改事件参数结构
2. 添加新的用户属性
3. 自定义性能监控指标
4. 实现自定义日志格式

## 故障排除

### 常见问题
1. **构建失败**: 检查 Gradle 配置和依赖版本
2. **Firebase 连接失败**: 验证 `google-services.json` 文件
3. **数据不显示**: 等待数据同步（24-48小时）
4. **崩溃报告不工作**: 检查 Crashlytics 配置

### 调试技巧
1. 查看 Android Studio Logcat 输出
2. 检查 Firebase Console 实时事件
3. 验证网络连接
4. 确认应用权限设置

## 相关文档

- [Firebase Android 设置指南](https://firebase.google.com/docs/android/setup)
- [Firebase Analytics 文档](https://firebase.google.com/docs/analytics)
- [Firebase Crashlytics 文档](https://firebase.google.com/docs/crashlytics)
- [Firebase Performance Monitoring 文档](https://firebase.google.com/docs/perf-mon)
- [Android 开发文档](https://developer.android.com/)