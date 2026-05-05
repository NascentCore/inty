# iMate (iOS)

仓库内 iMate 的 iOS 客户端 SwiftUI 工程。当前已打通 **登录 -> 鉴权动效 -> 多步初始化对话 -> 聊天页** 的导航与 UI 雏形；网络层与 Toast 已接入；聊天与初始化流程仍以本地状态与延时模拟为主，未接真实对话流。

## 技术栈

- Swift 5
- SwiftUI (`NavigationStack` + `NavigationPath`)
- iOS 16.0+ (App Target: `IPHONEOS_DEPLOYMENT_TARGET = 16.0`)
- iPhone + iPad (`TARGETED_DEVICE_FAMILY = "1,2"`)

## 工程信息

- Xcode 工程: `imate.xcodeproj`
- Bundle ID: `com.sxwl.imate`
- 版本号 (Marketing): `1.0`
- Build (Project Version): `1`
- Info.plist: `GENERATE_INFOPLIST_FILE = YES`

## 当前进度 (以代码为准)

- **启动入口**
  - `imateApp` -> `Entrance`
  - `GlobalToastOverlay` 挂载在 App 顶层 (`.overlay(...)`)
- **路由**
  - `Router` + `AppRoute`: `.login` `.loginEmail` `.loginEmailPassword` `.loginAuth` `.LoginInitChat` `.chatPage`
- **登录**
  - `LoginView`: 邮箱入口接路由；Apple 登录仍为占位
  - `LoginEmail`: 邮箱校验 (`ToolHelper.isValidEmail`)，写入 `UserManager.shared.email`
  - `LoginEmailPassword`: 调 `NetworkService` + `UserAPI.login`，Toast 反馈，成功后进入 `LoginAuth`
  - `LoginAuth`: Canvas 背景与进度条；结束后 `push(.LoginInitChat)`
- **初始化对话 (多步引导)**
  - `LoginInitChat` + `LoginInitChatVM` + `LoginInitStep` (step1~step5)
  - 流程概览: 输入称呼 -> 选择呈现性别/风格 -> 输入外观描述 -> 延时后收尾文案 -> 「完成」进入 `ChatPage`
  - 文案与占位提示集中在 `LoginConstants.InitChatMsg`
  - 消息模型: `ChatMessage` 定义于 `login/model/LoginInitChatModel.swift`，列表与输入条复用 `LoginInitChatWidgets`
- **聊天页**
  - `ChatPage` + `ChatPageVM`：首条消息来自 `ChatConstants.InitChatMsg`；发送后约 1 秒本地追加一条模拟回复
  - 顶栏可打开 `ChatSettingsSheet`（设置类文案占位，无真实登出/删号逻辑）
- **网络**
  - `NetworkService` + `APIEndpoint` + `APIResponse<T>` (`code` / `message` / `data`)
  - `UserAPI`: 基址 `https://dev.imate.inty.cc`，登录 path 当前为 `/api/v1/auth/google/login`
  - `LoginResponse` / `User` 与后端 snake_case 字段映射
- **全局提示**: `ToastManager` + `GlobalToastOverlay`

## 目录结构 (概览)

```text
imate_ios_app/
  README.md
  imate.xcodeproj/
  imate/
    imateApp.swift
    Entrance.swift
    router/
      AppRoute.swift
    login/
      Login.swift
      LoginConstants.swift
      model/
        LoginResponse.swift
        LoginInitChatModel.swift    # ChatMessage
      viewModel/
        LoginInitChatVM.swift       # LoginInitStep + 引导逻辑
      components/
        LoginWidgets.swift
        LoginInitChatWidgets.swift
      view/
        LoginEmail.swift
        LoginEmailPassword.swift
        LoginAuth.swift
        LoginInitChat.swift
    chat/
      ChatPage.swift
      ChatConstants.swift
      viewModel/
        ChatPageVM.swift
      components/
        ChatPageWidgets.swift
        ChatSettingsSheet.swift
    common/
      ColorExtension.swift
      UserManager.swift
      helper/
        ToolHelper.swift
      toast/
        ToastManager.swift
        GlobalToastOverlay.swift
      network/
        APIEndpoint.swift
        NetworkService.swift
        NetworkError.swift
        url/
          UserAPI.swift
    Assets.xcassets/
```

## 资源与注意事项

- `Image("logo")` 依赖 `Assets.xcassets/login/logo.imageset/`

## 依赖与测试

- 当前未引入 SPM / CocoaPods
- 本目录内未见单元测试 / UI 测试 target 源码

## 本地运行

1. Xcode 打开 `imate.xcodeproj`
2. 选择 `imate` scheme
3. 模拟器或真机运行

## 下一步 (最短路径)

- 登录成功后持久化 token (如 Keychain)，并在请求中自动带鉴权 Header
- `LoginAuth` 与初始化各步与后端状态对齐，失败可重试
- `ChatPage` / 初始化对话接入真实会话 API，替换本地延时回复
- `ChatSettingsSheet` 中登出、删号、条款等接真实逻辑或 WebView
