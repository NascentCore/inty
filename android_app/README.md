# AI 驱动的、面向北美年轻男性的亲密体验模拟 Android app（AI-driven intimacy simulation for NA young male adults）

[![Build release APK and AAB](https://github.com/NascentCore/inty-app/actions/workflows/ci.yaml/badge.svg)](https://github.com/NascentCore/inty-app/actions/workflows/ci.yaml)
[![Build and release debug APK](https://github.com/NascentCore/inty-app/actions/workflows/debug_release.yaml/badge.svg)](https://github.com/NascentCore/inty-app/actions/workflows/debug_release.yaml)

## Repo 初始化

```bash
# 同步 android_app/library/inty_sdk git module
# 不要进入这个目录修改
git submodule update --init --recursive
```

## Figma

下载 SF font：https://developer.apple.com/fonts/ 下载后安装

## Key setups

```bash
# Write a new key into the keystore file
keytool -genkeypair -keyalg RSA -keysize 2048 -validity 9125 \
    -keystore sign/intellimate-release-key.jks \
    -storetype JKS \
    -alias <alias of your new key> \
    -storepass <.jks file's password> \
    -keypass <password of your new key>

# Get the fingerprint from the key
keytool -keystore sign/intellimate-release-key.jks -list -v \
    -storepass <.jks file's password> \
    -alias <key alias>
```

Any new key must create an associated OAuth Client ID on Google Cloud.
And added to firebase fingerpints.
Then it can be used to sign the apk/aab to use Sign in with Google.

There are 2 keys used locally: dev, uploading.
The dev key is for general signing during development.
The uploading key is used to sign aab uploaded to Google Play.
Its fingerprint is recorded in Google Play, so Google Play can verify its authenticity.

`app/google-service.json` stores 3 OAuth client IDs, 2 of them are for the above 2 keys,
the last one is associated with Google Play's app signing key.

There are 4 OAuth client IDs created on Google Cloud.
3 of them are associated with the 3 keys above.
1 additional is the web client ID used by backend auth with Android app.
Which is used as `serverClientId` in [cerdential-manager-siwg](https://developer.android.com/identity/sign-in/credential-manager-siwg).

Google Cloud project and Firebase project is associated through the
`alien-paratext-461204-i9` project ID as well.

<img width="1514" height="1234" alt="image" src="https://github.com/user-attachments/assets/1d46e813-d3fd-48bb-adca-90a95691dc69" />

## Description

IntelliMate: Ultimate companionship, reimagined with AI

Role-play with AI characters. Create your own IntelliMate, powered by carefully tuned AI agents, experience your own imagination. 

* 将模拟器界面始终置于桌面前方，方便操作观察
  <img width="480" height="1678" alt="image" src="https://github.com/user-attachments/assets/cbd3f10f-f028-4103-a5f6-c997ba8b9eb9" />
* cmd+↑（放大模拟器设备界面）cmd+↓ （缩小模拟器设备界面）
* [adb shell monkey](https://developer.android.com/studio/test/other-testing-tools/monkey)

## 注意 ⚠️

* 安装应用来自 2 个来源，GitHub Release、Google Play 内测轨道
* 同一手机，只能选择 2 个来源之一，安装另一来源，需要删除原来源安装的版本
* 从 play console 移除 app：https://youtu.be/jEwYmvqMKL8?si=pCFg09NXtkJMSKsK（不是下架）
* `aapt dump badging /path/to/yourbuild.apk`
  * `aapt ${ANDROID_SDK_ROOT}/build-tools/<ANDROID_API_VERSION>/aapt`
* `bundletool dump manifest --bundle app/playdebug/app-playdebug.aab | grep versionCode`
  * `brew install bundletool`

## 提交 bug 报告时附带版本号

如果测试、使用中遇到 bug，采用录屏、截图的方式记录 bug 特征；并且附带版本号截图，方便工程师确认对应版本

<img width="250" alt="image" src="https://github.com/user-attachments/assets/9a47f539-9105-4810-9fe7-17d69c3f3a00" />
<img width="250" alt="image" src="https://github.com/user-attachments/assets/a19a99ed-4165-48e5-88d8-2aca17cfad0d" />

## Google Play uploading and signing

Uploading key is under app signing settings:

<img width="2304" height="1576" alt="image" src="https://github.com/user-attachments/assets/3a0ff063-3745-4109-8cb6-a78f5559d0a5" />

如需上传 aab，确保 versioncode，versioncode 来源于当前分支至 HEAD 为止的 commit 数量，
因此，如有必要，则需要写入新的 commit 来增加 version code。

## Overview

* Kotlin+Jetpack Compose
* Local development setup: <https://g.co/gemini/share/e068464e9dbd>
* [Daily release for testing](https://github.com/NascentCore/inty-app/releases)
  * 国内手机需要安装 Google 套件才能使用 Google 登录功能

### ✨ 核心功能

5 个底 tab，从左到右依次为：

1. Home (HomeTabIndex.Home) - The main chat interface where users can interact with AI agents
   * 聊天：用户左右滑动浏览推荐的 AI 角色
1. Activity (HomeTabIndex.Activity) - Shows conversation history and system messages
   * 聊天历史和关注角色
1. Create (HomeTabIndex.Create) - Special tab that navigates to role creation or login
   * 创建 AI 角色
1. Explore (HomeTabIndex.Explore) - Recommendation page showing suggested AI agents
   * AI 角色浏览
1. My (HomeTabIndex.My) - User profile and personal settings page
   * 我的：设置、创建的角色列表等

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

### 连接本地运行后端

**本机**运行后端，其端口位于`http://localhost:8000`；Android Studio，启动模拟器、或 USB 连接手机；需要使用 `adb` 命令行工具将本地服务端口映射到模拟器、手机上。

```bash
# 列出设备，记录自己使用的设备 ID
adb devices

# 将本机 :8000 端口映射到指定的设备
adb -s <device-id> reverse tcp:8000 tcp:8000
```

然后使用 `local` 构建模式（build type）来启动 App，该构建模式下，`baseUrl()`返回
`http://localhost:8000`。

安装`adb`：`adb`包含在 Android Platform Tools 内，Tools -> SDK Manager，
选择安装 Android SDK Platform Tools；将其路径加入 PATH：

```rc
PATH="/Users/yzhao/Library/Android/sdk/platform-tools:$PATH"
```

<img width="600" height="1408" alt="image" src="https://github.com/user-attachments/assets/47cd8996-afef-41a4-b039-383e5bf167cf" />

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

### 构建类型（build type）

* **Debug**（默认）: 开发构建，包含调试工具，Android 自带构建类型；后端指向共享的开发环境
* **Local**：继承自 Debug 指向本地运行的后端
* **Release**: 生产构建，用于分发，Android 自带构建类型；后端指向生成环境
* **Playdebug**：继承自 Release 指向共享的开发环境

### 🧪 测试

```bash
# 单元测试
./gradlew test

# 仪器测试  
./gradlew connectedAndroidTest

# 特定测试类
./gradlew test --tests "com.ai.inty.ExampleUnitTest"
```

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

<img width="960" height="1040" alt="image" src="https://github.com/user-attachments/assets/2ec97c47-07f0-4cfb-85b4-57dba7222925" />

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

* `versionCode`: 取自 git commit count
* `versionName`: 语义版本控制 (例如 1.0.1)
* 调试构建包含 git 提交哈希: `1.0.1 (d799932)`
* `bundletool dump manifest --bundle app/playdebug/app-playdebug.aab | grep versionCode` 查看 aab 版本信息

## 参考

* [Jetpack Compose](https://developer.android.com/jetpack/compose) 用于现代 UI 开发
* [TheRouter](https://github.com/HuolalaTech/hll-wp-therouter-android) 用于导航
* [MMKV](https://github.com/Tencent/MMKV) 用于高效存储
* [Coil](https://coil-kt.github.io/coil/) 用于图片加载
* [Firebase](https://firebase.google.com/) 用于后端服务
