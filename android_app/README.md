# android_应用程序

AI驱动的、针对北美年轻男性的亲密体验模拟Android app（AI驱动的北美年轻男性亲密体验模拟）

[![构建发布 APK 和 AAB](https://github.com/NascentCore/inty-app/actions/workflows/ci.yaml/badge.svg)](https://github.com/NascentCore/inty-app/actions/workflows/ci.yaml)
[！[构建并发布调试 APK](https://github.com/NascentCore/inty-app/actions/workflows/debug_release.yaml/badge.svg)](https://github.com/NascentCore/inty-app/actions/workflows/debug_release.yaml)```text
IntelliMate: Ultimate companionship, reimagined with AI
Role-play with AI characters.
Create your own IntelliMate, powered by carefully tuned AI agents,
experience your own imagination.
```＃＃ 概述

- Kotlin+Jetpack Compose
- 本地开发设置：<https://g.co/gemini/share/e068464e9dbd>
- [每日发布测试](https://github.com/NascentCore/inty-app/releases)
  - 手机国内需要安装Google套件才能使用Google登录功能
- 将模拟器界面置于桌面前方，方便操作观察
  ！[图片](https://github.com/user-attachments/assets/cbd3f10f-f028-4103-a5f6-c997ba8b9eb9)
- cmd+↑（放大模拟器设备界面）cmd+↓（缩小模拟器设备界面）
- [adb shell 猴子](https://developer.android.com/studio/test/other-testing-tools/monkey)

## 回购初始化```bash
git clone git@github.com:NascentCore/inty.git
cd inty/android_app
# 同步 android_app/library/inty_sdk git module
# 不要进入这个目录修改
git submodule update --init --recursive
```## 关键设置```bash
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
```任何新密钥都必须在 Google Cloud 上创建关联的 OAuth 客户端 ID。
并添加到 firebase Finger-pints 中。
然后它可以用来签署apk/aab以使用Google登录。

本地使用的键有2个：dev、uploading。
开发密钥用于开发期间的常规签名。
上传密钥用于对上传到 Google Play 的 aab 进行签名。
它的fingerprint被记录在Google Play中，因此Google Play可以验证其真实性。`app/google-service.json`存储 3 个 OAuth 客户端 ID，其中 2 个用于上述 2 个密钥，
最后一个与 Google Play 的应用程序签名密钥相关联。

在 Google Cloud 上创建了 4 个 OAuth 客户端 ID。
其中 3 个与上面的 3 个键相关联。
另外 1 个是后端身份验证使用 Android 应用程序使用的 Web 客户端 ID。哪个用作`serverClientId`在 [cerdential-manager-siwg](https://developer.android.com/identity/sign-in/credential-manager-siwg) 中。Google Cloud project 和 Firebase project 通过以下方式关联`alien-paratext-461204-i9`project ID 也是如此。

！[图片](https://github.com/user-attachments/assets/1d46e813-d3fd-48bb-adca-90a95691dc69)

## 🏗️架构设计

**本机**运行遥控器，其端口位于`http://localhost:8000`；Android Studio，启动模拟器、或USB连接手机；需要使用`adb` 命令行工具将本地服务端口映射到模拟器、手机上。

```bash
# 列出设备，记录自己使用的设备 ID
adb devices

# 将本机 :8000 端口映射到指定的设备
adb -s <device-id> reverse tcp:8000 tcp:8000
```

然后使用 `local`构建模式（build type）来启动App，该构建模式下，`baseUrl()`返回
`http://localhost:8000`。

安装`adb`：`adb`包含在 Android Platform Tools 内，Tools -> SDK Manager，
选择安装Android SDK Platform Tools；将其路径加入PATH：```rc
PATH="/Users/yzhao/Library/Android/sdk/platform-tools:$PATH"
```！[图片](https://github.com/user-attachments/assets/47cd8996-afef-41a4-b039-383e5bf167cf)

## 参考

- [Jetpack Compose](https://developer.android.com/jetpack/compose) 用于现代 UI 开发
- 最初的Intent导航系统
- [MMKV](https://github.com/Tencent/MMKV) 用于高效存储
- [线圈](https://coil-kt.github.io/coil/) 用于图片加载
- [Firebase](https://firebase.google.com/) 用于硬件服务

## Cursor 摘要

- 栈与导航：Kotlin + Jetpack Compose 构建 UI；以 Activity/Intent 为主的导航；Compose 组件集中在`app/src/main/kotlin/com/ai/intellimate`。
- 模块划分:
  - `app`: 功能入口与特性页面（聊天、探索、角色信息/生成、VIP/订阅、登录、设置/资料、音频/TTS），包含ViewModel与Activity。
  -`core/common`: 基础Activity/ViewModel、分析埋点、事件跟踪、启动与通用工具。
  -`core/data`: 领域模型与仓库；API 接口（`IUserApi`/`IChatApi`/`IAgentApi`/`ISubscriptionApi`）与 `IntyNetworkManager`。
  - `core/design`: 主题（`Color`/`Type`/`Theme`等）与可复用 Compose UI 组件与工具。
  -`core/firebase`：Firebase初始化、FCM主动服务与管理。
  -`library/network`: 轻量网络层与CallAdapter（自定义响应包装）。
  -`library/utils`: 图片压缩/网络等工具集合。
  - `build-logic/convention`: Gradle 约定式插件（Compose/Navigation/Kotlin Android 等）。
 - 网络与环境：`core/data` 通过自定义网络层访问后端；构建类型决定 `baseUrl`；`local` 对应 `http://localhost:8000`，通过 `adb 反向`映射。
 - 数据与存储：使用 MMKV 本地存储（见仓库引用）。
 - 计费：集成 Google Play Billing（`BillingRepository` 及价格/购买/状态管理器）。
 - 音频/语音: TTS 与音频播放/缓存管理（`TtsManager`/`AudioPlaybackManager`/`VoicePlayer`等）。
 - 主动通知：Firebase Cloud Messaging 集成。
 - 分页：聊天/探索采用 PagingSource 与仓库封装。
 - 工程化：版本库（libs.versions.toml）、ProGuard 规则、与 CI 构建逻辑。