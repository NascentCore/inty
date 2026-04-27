# iMate (iOS)

仓库内 iMate 的 iOS 客户端 SwiftUI 工程。目前已完成登录-鉴权加载-初始化对话-聊天页的基础链路雏形，并接入了最小可用的网络请求层与全局 Toast。

## 技术栈

- Swift 5
- SwiftUI (`NavigationStack` + `NavigationPath`)
- iOS 16.0+ (Target: `IPHONEOS_DEPLOYMENT_TARGET = 16.0`)
- iPhone + iPad (`TARGETED_DEVICE_FAMILY = "1,2"`)

## 工程信息

- Xcode 工程: `imate.xcodeproj`
- Bundle ID: `com.sxwl.imate`
- 版本号 (Marketing): `1.0`
- Build (Project Version): `1`
- Info.plist: `GENERATE_INFOPLIST_FILE = YES`

## 当前进度 (以代码为准)

- 启动入口
  - `imateApp` -> `Entrance`
  - `GlobalToastOverlay` 已挂载到 App 顶层 (`.overlay(...)`)
- 路由骨架
  - `Router` (基于 `NavigationPath`) + `AppRoute`
  - 路由枚举包含: `.login` `.loginEmail` `.loginEmailPassword` `.loginAuth` `.LoginInitChat` `.chatPage`
- 登录链路
  - `LoginView`: 邮箱登录入口已接入路由; Apple 登录仍为占位
  - `LoginEmail`: 邮箱输入 + 校验 (`ToolHelper.isValidEmail`), 写入 `UserManager.shared.email`
  - `LoginEmailPassword`: 调用后端登录接口并显示 toast; 成功后进入 `LoginAuth`
  - `LoginAuth`: Canvas 背景 + 进度条动画; 动画结束后进入 `LoginInitChat`
- 初始化对话页
  - `LoginInitChat`: 类聊天 UI + 进度条(模拟), 当前仅本地追加消息/推进进度
- 聊天页
  - `ChatPage`: 消息列表 + 输入框, 当前仅本地追加消息 (未接后端对话)
- 网络层 (已接入)
  - `NetworkService.shared.request(...)` 支持 `APIEndpoint` 并按通用结构 `APIResponse<T>` (`code/message/data`) 解包
  - `UserAPI.login(email:password:)` 基础 URL: `https://dev.imate.inty.cc`
    - 当前 path: `/api/v1/auth/google/login`
  - `LoginResponse`/`User` 已按后端字段 (snake_case) 做解码映射
- 全局提示
  - `ToastManager.shared.show(...)` + `GlobalToastOverlay`

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
      model/
        LoginResponse.swift
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
      components/
        ChatPageWidgets.swift
    common/
      ColorExtension.swift
      UserManager.swift
      helper/
        ToolHelper.swift
      toast/
        ToastManager.swift
        GlobalToastOverlay.swift
      Network/...
      network/...
    Assets.xcassets/
```

## 资源与注意事项

- `Image("logo")` 依赖 `Assets.xcassets/login/logo.imageset/`
- `common/Network/...` 与 `common/network/...` 同时存在, 目前是重复目录形态 (大小写不同). 文档按现状保留描述, 后续若要收敛建议统一命名并清理引用.

## 依赖与测试

- 当前未引入 SPM/CocoaPods 依赖
- 未见单元测试 / UI 测试源码

## 本地运行

1. Xcode 打开 `imate.xcodeproj`
2. 选择 `imate` scheme
3. 选择模拟器或真机运行

## 下一步 (从现状最短路径)

- 登录成功后保存 token (例如 Keychain), 并在 `NetworkService` 自动注入鉴权 Header
- `LoginAuth` 的动画完成逻辑改为依据真实网络状态/初始化结果推进路由
- `LoginInitChat` 与 `ChatPage` 接入真实对话接口 (替换本地 mock 消息)
- 收敛 `common/Network` vs `common/network` 重复目录, 避免大小写路径在不同文件系统下产生问题