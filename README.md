# AI intimacy simulation for young male adults

[![Build release APK and AAB](https://github.com/NascentCore/inty-app/actions/workflows/ci.yaml/badge.svg)](https://github.com/NascentCore/inty-app/actions/workflows/ci.yaml)

## 提交 bug 报告时附带版本号

如果测试、使用中遇到 bug，采用录屏、截图的方式记录 bug 特征；并且附带版本号截图，方便工程师确认对应版本

<img width="350" alt="image" src="https://github.com/user-attachments/assets/9a47f539-9105-4810-9fe7-17d69c3f3a00" />
<img width="350" alt="image" src="https://github.com/user-attachments/assets/a19a99ed-4165-48e5-88d8-2aca17cfad0d" />

## Google Play uploading and signing

Uploading key is under app signing settings:

<img width="2304" height="1576" alt="image" src="https://github.com/user-attachments/assets/3a0ff063-3745-4109-8cb6-a78f5559d0a5" />

## Overview

* Kotlin+Jetpack Compose
* Local development setup: <https://g.co/gemini/share/e068464e9dbd>
* [Daily release for testing](https://github.com/NascentCore/inty-app/releases)
  * 国内手机需要安装 Google 套件才能使用 Google 登录功能

### ✨ 核心功能

* 🤖 **AI 伙伴**: 与多样化的 AI 个性聊天
* 👤 **自定义角色**: 创建和定制您自己的 AI 伙伴
* 🎨 **AI 头像生成**: 使用 AI 生成独特头像
* 💬 **实时聊天**: 无缝消息体验
* 🔊 **语音消息**: 音频播放支持
* 📱 **Google 登录**: 安全认证，支持游客模式
* 💎 **高级功能**: 应用内购买和订阅
* 🌍 **多语言**: 国际化支持
* 🔒 **隐私优先**: 无广告跟踪，注重隐私的设计

## 🏗️ 架构设计

### 技术栈

* **开发语言**: 100% Kotlin
* **UI 框架**: Jetpack Compose + Material3 设计
* **架构模式**: MVVM (Model-View-ViewModel)
* **导航框架**: TheRouter (基于 URL 的路由)
* **网络层**: Retrofit + OkHttp，自定义 HttpResult 封装
* **状态管理**: StateFlow + MMKV 持久化
* **图片加载**: Coil3 异步加载
* **依赖注入**: TheRouter 的 @Singleton 和 @Autowired

## 🚀 快速开始

### 环境要求

* Android Studio Hedgehog | 2023.1.1 或更新版本
* JDK 17 (推荐使用 Android Studio 内置的 JBR)
* Android SDK API 29+ (Android 10+)
* Git 版本控制

### 设置步骤

1. **克隆仓库**

   ```bash
   git clone https://github.com/NascentCore/inty-app.git
   cd inty-app
   ```

2. **配置签名**

   ```bash
   # 复制模板并填入您的密钥库详细信息
   cp keystore.properties.template keystore.properties
   # 编辑 keystore.properties 填入实际的签名信息
   ```

3. **环境设置**

   ```bash
   # 设置 Java 环境 (构建必需)
   export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
   ```

4. **构建项目**

   ```bash
   # 构建调试 APK
   ./gradlew assembleDebug
   
   # 构建发布版 AAB (用于 Play Store)
   ./gradlew bundleRelease
   
   # 运行测试
   ./gradlew test
   
   # 清理构建
   ./gradlew clean
   ```

### 配置文件

#### 必需文件

* `keystore.properties` - 签名配置 (从模板创建)

* `app/google-services.json` - Firebase 配置
* `local.properties` - SDK 路径配置

#### 重要：安全设置

```bash
# 确保 keystore.properties 配置正确
echo "keystore.properties" >> .gitignore  # 已配置
```

## 🛠️ 开发指南

### 构建变体

* **Debug**: 开发构建，包含调试工具
  * 包含 Chucker 网络检查
  * 版本名包含 git 提交哈希
  * 使用调试签名配置
  
* **Release**: 生产构建，用于分发
  * 启用代码混淆和资源压缩
  * 使用发布签名配置
  * 性能优化

### 关键开发工具

#### 网络调试

```kotlin
// Chucker 集成 (仅调试构建)
debugImplementation("com.github.chuckerteam.chucker:library:3.5.2")
releaseImplementation("com.github.chuckerteam.chucker:library-no-op:3.5.2")
```

#### 日志系统

```kotlin
// 使用 EasyLog 自定义日志
EasyLog.log("调试消息")
EasyLog.log("发生错误", EasyLog.ERROR)
```

#### 状态管理

```kotlin
// 使用 StateFlow 实现响应式 UI
private val _messages = MutableStateFlow<List<Message>>(emptyList())
val messages = _messages.asStateFlow()
```

## 🔧 配置

### Firebase 设置

1. **创建 Firebase 项目**
   * 访问 [Firebase 控制台](https://console.firebase.google.com/)
   * 创建新项目或使用现有项目

2. **添加 Android 应用**
   * 包名: `com.ai.inty`
   * 下载 `google-services.json`
   * 放置在 `app/` 目录中

3. **启用服务**
   * 身份验证 (Google 登录)
   * 云消息传递 (推送通知)
   * 分析 (可选)

### Google OAuth 配置

1. **Google Cloud 控制台**
   * 导航到 [Google Cloud 控制台](https://console.cloud.google.com/)
   * 为 Android 创建 OAuth 2.0 客户端 ID
   * 添加调试和发布密钥库的 SHA-1 指纹

2. **SHA-1 指纹**

   ```bash
   # 获取调试密钥库 SHA-1
   keytool -list -v -keystore sign/key.jks -alias key0
   
   # 获取发布密钥库 SHA-1  
   keytool -list -v -keystore sign/my-release-key.jks -alias my-key-alias
   ```

### 应用内购买设置

在 Google Play 控制台配置计费：

* 创建订阅产品
* 设置定价和可用性
* 使用许可证测试员进行测试

## 📱 功能深度解析

### 聊天系统

* 与 AI 角色实时消息传递

* 动作文本的消息样式 `(动作文本)`
* 持续对话的保持通话功能
* 角色特定和全局设置

### 角色管理

* 关注/取消关注 AI 角色

* 使用 AI 生成头像创建自定义角色
* 背景图像和个性设置
* 语音偏好和互动风格

### 用户体验

* 导航的边缘滑动手势

* 带有动态背景的沉浸式 UI
* 键盘感知布局
* 直观的材料设计

## 🔒 隐私与安全

### 隐私功能

* **无广告跟踪**: 明确禁用广告 ID 收集
* **数据最小化**: 仅收集必要的用户数据
* **安全存储**: 本地数据的 MMKV 加密
* **仅 HTTPS**: 所有网络通信加密

### 安全措施

* 发布构建中的 ProGuard 混淆

* 使用安全密钥库签名的 APK/AAB
* Firebase 安全规则实现
* 输入验证和清理

## 📦 依赖项

### 核心依赖

```kotlin
// UI 和架构
implementation("androidx.activity:activity-compose:1.8.2")
implementation("androidx.compose.material3:material3")
implementation("androidx.lifecycle:lifecycle-viewmodel-compose")

// 网络
implementation("com.squareup.retrofit2:retrofit:2.9.0")
implementation("com.squareup.okhttp3:okhttp:4.12.0")

// 图片加载
implementation("io.coil-kt.coil3:coil-compose:3.2.0")

// 存储和日志
implementation("com.tencent:mmkv:1.3.5")
implementation("com.tencent.mars:mars-xlog:1.2.6")

// Firebase
implementation(platform("com.google.firebase:firebase-bom:32.7.0"))
implementation("com.google.firebase:firebase-analytics")
implementation("com.google.firebase:firebase-messaging")

// 导航和依赖注入
implementation("cn.therouter:router:1.2.3")
implementation("com.google.android.gms:play-services-auth:21.2.0")
```

## 🧪 测试

### 运行测试

```bash
# 单元测试
./gradlew test

# 仪器测试  
./gradlew connectedAndroidTest

# 特定测试类
./gradlew test --tests "com.ai.inty.ExampleUnitTest"
```

### 测试结构

* ViewModels 和业务逻辑的单元测试

* 网络层的集成测试
* 关键用户流程的 UI 测试

## 🚀 部署

### Play Store 发布

1. **构建发布版 AAB**

   ```bash
   ./gradlew bundleRelease
   ```

2. **上传到 Play 控制台**
   * 导航到 Google Play 控制台
   * 从 `app/build/outputs/bundle/release/` 上传 AAB 文件
   * 填写发布说明和元数据

3. **Play Store 要求**
   * 目标 SDK 34+ (Android 14)
   * 需要应用包格式
   * 隐私政策和数据安全声明
   * 内容评级问卷

### 版本管理

版本信息自动管理：

* `versionCode`: 每次发布递增
* `versionName`: 语义版本控制 (例如 1.0.1)
* 调试构建包含 git 提交哈希: `1.0.1 (d799932)`

## 🤝 贡献

### 开发工作流程

1. **Fork 仓库**
2. **创建功能分支**

   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **进行更改**
   * 遵循代码风格指南
   * 为新功能添加测试
   * 根据需要更新文档
4. **提交更改**

   ```bash
   git commit -m "添加惊人功能"
   ```

5. **推送并创建 PR**

   ```bash
   git push origin feature/amazing-feature
   ```

### 代码审查指南

* 确保所有测试通过

* 遵循既定的架构模式
* 包含适当的错误处理
* 更新相关文档

## 参考

* [Jetpack Compose](https://developer.android.com/jetpack/compose) 用于现代 UI 开发
* [TheRouter](https://github.com/HuolalaTech/hll-wp-therouter-android) 用于导航
* [MMKV](https://github.com/Tencent/MMKV) 用于高效存储
* [Coil](https://coil-kt.github.io/coil/) 用于图片加载
* [Firebase](https://firebase.google.com/) 用于后端服务
