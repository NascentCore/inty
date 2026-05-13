# imate（iOS）

仓库内 **iMate** 的 iOS 客户端 **SwiftUI 雏形工程**，当前以登录页视觉与导航骨架为主，业务与账号体系尚未接入。

## 技术栈

- **语言**：Swift 5  
- **UI**：SwiftUI  
- **最低系统**：iOS 16.0（以 Xcode Target 配置为准）  
- **设备**：iPhone + iPad  

## 目录结构
imate_ios_app/ ├── imate.xcodeproj/ # Xcode 工程 └── imate/ ├── imateApp.swift # @main 入口 ├── Entrance.swift # 根场景：NavigationStack + Router ├── MainTabView.swift # Tab 骨架（当前未被入口使用） ├── router/ │ └── AppRoute.swift # AppRoute 枚举 + Router（NavigationPath） ├── login/ │ ├── Login.swift # LoginView │ └── components/ │ └── LoginWidgets.swift # 登录页子视图（背景、文案、按钮、条款） ├── home/ │ └── HomeView.swift # 占位首页 ├── common/ │ └── ColorExtension.swift # Color(hex:) 扩展 └── Assets.xcassets/ # AppIcon、AccentColor 等


## 应用流程（当前实现）

1. 启动：`imateApp` → `Entrance`  
2. `Entrance` 使用 `NavigationStack(path:)` 绑定 `Router.path`，根视图为 `LoginView`  
3. `AppRoute` 提供 `.login`、`.home`；`Router` 提供 `push` / `pop` / `popToRoot`  
4. 登录页按钮尚未调用 `router.push(.home)`，首页仍为模板；首页已提供开发期 Live Chat 语音通话表单，用于填入后端地址、Bearer token 与 agent id 后手动验证实时语音通话。

## 实时语音通话雏形

- `voicecall/VoiceCallWebSocketClient.swift` 使用 `URLSessionWebSocketTask` 连接 `/api/v1/live-chat/{agent_id}`，通过 Bearer token 鉴权。
- `voicecall/VoiceCallAudioEngine.swift` 使用 `AVAudioEngine` 采集麦克风音频并播放后端返回的 PCM 音频。
- `voicecall/VoiceCallView.swift` 提供最小 Start / End UI。
- 工程使用自动生成 Info.plist，并在 build setting 中写入 `NSMicrophoneUsageDescription`。

## 工程信息

| 项 | 值 |
|----|-----|
| Bundle ID | `com.sxwl.imate` |
| 营销版本 | 1.0 |

## 依赖与测试

- **Swift Package**：工程中未声明 `packageProductDependencies`  
- **单元测试 / UI 测试**：本目录内未见测试 Target 源码  

## 后续可完善方向（建议）

- 接入真实 **Sign in with Apple** / 邮箱登录与后端会话  
- 登录成功后 `push(.home)` 或替换根视图，并落地首页产品 UI  
- 删除或合并未使用的 `MainTabView`，统一一套 `Router` 与路由表  
- 替换登录页占位图形为正式 Logo 与本地化文案  

## 本地运行

使用 **Xcode** 打开 `imate.xcodeproj`，选择 `imate` scheme，在模拟器或真机运行。