# IntelliMate Android App 代码

IntelliMate Android App 全部代码位于本目录下。
IntelliMate AI 驱动的、面向北美年轻男性的亲密体验模拟 Android app（AI-driven intimacy simulation for NA young male adults）

```text
IntelliMate: Ultimate companionship, reimagined with AI
Role-play with AI characters.
Create your own IntelliMate, powered by carefully tuned AI agents,
experience your own imagination.
```

## Overview

- Kotlin+Jetpack Compose
- 将模拟器界面始终置于桌面前方，方便操作观察
  ![image](https://github.com/user-attachments/assets/cbd3f10f-f028-4103-a5f6-c997ba8b9eb9)
- cmd+↑（放大模拟器设备界面）cmd+↓ （缩小模拟器设备界面）
- [adb shell monkey](https://developer.android.com/studio/test/other-testing-tools/monkey)

## 新人速览：产品概念与功能模式

- **角色（Agent）模型**：后端定义基础人设（人格、口癖、价值观、剧情约束）并在 `core/data/agent` 内落地为 `AgentProfile` 与 `AgentState`，前端可在「探索页」展示精选角色，也可通过 `CharacterBuilder` 让用户自定义头像、语气、背景故事。Agent 的 prompt/traits 会同步影响聊天回复、动态背景、推荐语音包。
- **主导航结构**：底部导航通常包含「探索/Discover」「聊天/Chat」「故事/Storylines」「个人/Me」。探索页是瀑布流列表（Compose `LazyVerticalGrid`），聊天页是会话列表+消息流（`ChatConversationScreen`），个人页负责资料、设置与快捷入口。理解每个 Tab 的数据来源（Repository 层）可以帮助快速定位问题。
- **核心互动循环**：典型路径为 Onboarding → 选择/创建 Agent → 进入聊天（文本 + 语音 + 卡片行动）→触发 TTS/音频 → 推送提醒用户回流。聊天消息由流式接口返回，配合 `MessageTimelineState` 负责打字机动画、语音播放与多模态展示。
- **情绪与排程机制**：Agent 会通过「心情状态」控件呈现情绪（开心、害羞、神秘等），并伴随「剧情节点」卡片引导用户解锁下一段剧情。`PushSchedulerService` 根据剧情进度安排推送，保持陪伴感。
- **付费与解锁模式**：订阅（VIP）是主线变现点，位于「聊天顶部横幅」「付费墙弹窗」「个人页订阅卡」。免费用户有每日限额、语音锁定或高级剧情锁定，`BillingRepository` 与 `SubscriptionGate` 统一判断各功能是否可用。新人可先查 `core/data/subscription` 了解 entitlement 判定。
- **内容安全与审核**：文本/语音在后端已做大部分审核，客户端侧仍提供「举报」「拉黑」「语气调节」入口（多在消息长按菜单或个人页）。设计上所有风险操作都需显式二次确认。
- **媒体表现层**：角色头像、背景视频、语音播放为塑造沉浸感的关键；`AnimatedBackground` 根据 Agent 标签切换动态素材，TTS 音色与角色绑定，情绪 icon 与聊天泡泡颜色一致，保证视觉一致性。
- **运营能力**：`AnnouncementBanner`、`InAppSurvey` 与 `EventBadge` 可在不发版情况下定向透出活动。工作流：远端配置（Firebase Remote Config/自研配置）→ `core/data/settings` 拉取 → Compose Banner 解析渲染。
- **用户数据存储**：轻量状态（开关、最近播放音色）存 MMKV，重要状态（角色收藏、剧情进度）依赖后端。不要在纯前端状态上做关键判断，以免与服务器不一致。

## 媒体缓存速览

- `AudioCacheManager` + `AudioPreloadManager`：`app/src/main/kotlin/com/ai/intellimate/audio/` 中使用 `LruCache<String, ByteArray>` 与 `context.cacheDir/audio_cache` 双层缓存开场白/消息语音，`UnifiedStartupManager` 启动阶段批量预热，命中后直接从内存或本地文件播放。
- `VideoCacheManager`：`app/src/main/kotlin/com/ai/intellimate/ui/components/VideoCacheManager.kt` 把背景动画视频下载到 `context.cacheDir/video_cache`，内存仅存文件路径并同步至 `IntySetting`，`AnimatedBackground`、`AgentBackground` 以及启动流程调用 `preloadVideo()` 缓解首次加载黑屏。
- `AdvancedCoilConfig` + `ImagePreloadManager`：`core/design` 为 Coil 配置 40% 内存 + 5% 磁盘缓存（目录 `context.cacheDir/image_cache`），`core/common/startup/ImagePreloadManager` 在推荐/聊天 agent 到手后批量 `preloadAgentsImages()`，保证头像与背景图片快速命中。

## 运行脚本化点击测试（UIAutomator）

前置条件：
- 已连接且解锁的模拟器或真机（可用 `adb devices` 检查）
- 可以正常安装/启动 `app` 的 Debug 构建

测试类路径：`app/src/androidTest/kotlin/com/ai/intellimate/ScriptedClickTest.kt`

在 Android Studio 中运行：
- 打开上述测试类，右键运行“Run 'ScriptedClickTest'”，选择目标设备

命令行运行（推荐从 `android_app/` 目录执行）：

```bash
cd android_app
# 仅运行该测试类（Debug 变体）
ANDROID_SERIAL=<device_id 可选> \
./gradlew :app:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=com.ai.intellimate.ScriptedClickTest

# 运行模块内所有 androidTest（Debug 变体）
ANDROID_SERIAL=<device_id 可选> ./gradlew :app:connectedDebugAndroidTest
```

小贴士：
- 若首次启动会弹出权限对话框，测试会尝试点击“允许/Allow/OK”；若设备语言不同，可在 `ScriptedClickTest` 的 `steps` 中增删 `ClickText/ClickDesc/ClickResId/Wait/Back` 等步骤以匹配实际界面。
- 若连接多台设备，可通过设置 `ANDROID_SERIAL=<device_id>` 指定目标设备（用 `adb devices` 获取 `device_id`）。

## Repo 初始化

```bash
git clone git@github.com:NascentCore/inty.git
cd inty/android_app
# 同步 android_app/library/inty_sdk git module
# 不要进入这个目录修改
git submodule update --init --recursive
```

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
And added to firebase finger-pints.
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
Which is used as `serverClientId`
in [cerdential-manager-siwg](https://developer.android.com/identity/sign-in/credential-manager-siwg).

Google Cloud project and Firebase project is associated through the
`alien-paratext-461204-i9` project ID as well.

![image](https://github.com/user-attachments/assets/1d46e813-d3fd-48bb-adca-90a95691dc69)

## 🏗️ 架构设计

**本机**运行后端，其端口位于`http://localhost:8000`；Android Studio，启动模拟器、或 USB 连接手机；需要使用
`adb` 命令行工具将本地服务端口映射到模拟器、手机上。

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

![image](https://github.com/user-attachments/assets/47cd8996-afef-41a4-b039-383e5bf167cf)

## 参考

- [Jetpack Compose](https://developer.android.com/jetpack/compose) 用于现代 UI 开发
- 原生Intent导航系统
- [MMKV](https://github.com/Tencent/MMKV) 用于高效存储
- [Coil](https://coil-kt.github.io/coil/) 用于图片加载
- [Firebase](https://firebase.google.com/) 用于后端服务

## Cursor Summary

- 栈与导航: Kotlin + Jetpack Compose 构建 UI；以 Activity/Intent 为主的导航；Compose 组件集中在 `app/src/main/kotlin/com/ai/intellimate`。
- 模块划分:
  - `app`: 功能入口与特性页面（聊天、探索、角色信息/生成、VIP/订阅、登录、设置/资料、音频/TTS），含 ViewModel 与 Activity。
  - `core/common`: 基础 Activity/ViewModel、分析埋点、事件总线、启动与通用工具。
  - `core/data`: 领域模型与仓库；API 接口（`IUserApi`/`IChatApi`/`IAgentApi`/`ISubscriptionApi`）与 `IntyNetworkManager`。
  - `core/design`: 主题（`Color`/`Type`/`Theme` 等）与可复用 Compose UI 组件与工具。
  - `core/firebase`: Firebase 初始化、FCM 推送服务与管理。
  - `library/network`: 轻量网络层与 CallAdapter（自定义响应包装）。
  - `library/utils`: 图片压缩/网络等工具集合。
  - `build-logic/convention`: Gradle 约定式插件（Compose/Navigation/Kotlin Android 等）。
 - 网络与环境: `core/data` 通过自定义网络层访问后端；构建类型决定 `baseUrl`；`local` 对应 `http://localhost:8000`，通过 `adb reverse` 映射。
 - 数据与存储: 使用 MMKV 本地存储（见仓库引用）。
 - 计费: 集成 Google Play Billing（`BillingRepository` 及价格/购买/状态管理器）。
 - 音频/语音: TTS 与音频播放/缓存管理（`TtsManager`/`AudioPlaybackManager`/`VoicePlayer` 等）。
 - 推送通知: Firebase Cloud Messaging 集成。
 - 分页: 聊天/探索采用 PagingSource 与仓库封装。
 - 工程化: 版本库（libs.versions.toml）、ProGuard 规则、构建逻辑与 CI。

## core 模块为何仍独立存在？

- `core/common`、`core/design`、`core/data` 虽是 Kotlin Library Module，但它们不仅抽象了“可被多个 App 复用”的能力，更重要的是在单 App 场景下提供清晰依赖边界：`app` 只能向下依赖，禁止横向互调，避免 Activity/Feature 间耦合。
- 模块化带来的增量编译、Gradle 配置隔离与测试可控性，与是否拥有第二个 App 无关；单 App 仍可通过拆分模块获得更快的全量/增量构建与更清晰的代码所有权。
- `core/design` 统一维护主题、组件与资源，阻止 UI 资产散落在 `app` 中；未来若出现 Wear/Tablet/WebView 外壳或动态 Feature，可直接依赖该模块。
- `core/data` 聚合网络、仓库、用例、支付、设置等领域逻辑，本身已经是跨 UI 层可复用的“数据内核”；即便暂时只有主 App，也能在实验模块或 UIAutomator 测试中直接复用。
- `core/common` 收敛基类、埋点、事件系统、启动优化等基建，任何 Feature 需要的通用能力都从此获取，杜绝散落的 util/单例实现。
- 若未来新增多端/多壳，现有模块可以直接被依赖；若没有，则也只增加了极小的 Gradle 配置成本，不会影响运行时体积或性能。

## 模块依赖约束机制

**禁止横向互调**（如 `core/data` 不能调用 `core/design`）通过以下机制实现：

- **依赖层次结构**：`app` → `core/*` → `library/*`，单向依赖，禁止同级模块互调
- **Gradle 配置约束**：在 `build.gradle.kts` 中不添加横向依赖，编译时 classpath 中不存在
- **编译时检查**：Kotlin 编译器自动检查，尝试 `import` 未依赖模块的类会编译失败
- **架构约定**：通过文档和代码审查确保依赖关系符合架构设计
- **实际效果**：`core/data` 和 `core/design` 互不依赖，只能通过上层模块（如 `core/common` 或 `app`）间接使用
