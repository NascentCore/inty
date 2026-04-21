# iMate（iOS）

仓库内 **iMate** 的 iOS 客户端 **SwiftUI 雏形工程**。当前重点是登录相关页面与导航骨架；账号体系、后端会话与真实鉴权尚未接入。

## 技术栈

- **语言**：Swift（`SWIFT_VERSION = 5.0`）
- **UI**：SwiftUI（`NavigationStack` + `NavigationPath`）
- **最低系统**：iOS **16.0**（Target 配置：`IPHONEOS_DEPLOYMENT_TARGET = 16.0`）
- **设备**：iPhone + iPad（`TARGETED_DEVICE_FAMILY = "1,2"`）

## 工程信息

- **Xcode 工程**：`imate.xcodeproj`
- **Bundle ID**：`com.sxwl.imate`
- **版本号（Marketing）**：`1.0`
- **Build（Project Version）**：`1`
- **Info.plist**：使用 `GENERATE_INFOPLIST_FILE = YES`（工程内未单独维护 Info.plist 文件）

## 当前功能与页面

- **启动入口**：`imateApp` → `Entrance`
- **路由**：`Router`（`NavigationPath`）+ `AppRoute`
  - `.login`
  - `.home`
  - `.loginEmail`
  - `.loginEmailPassword`
  - `.loginAuth`

- **登录主页面**：`LoginView`
  - “Continue with Email” 已接入路由：跳转到 `LoginEmail`
  - “Continue with Apple” 目前未实现逻辑（占位）
- **邮箱输入页**：`LoginEmail`
  - 基础输入与跳转逻辑已写入（当前继续按钮直接进入密码页，校验逻辑留有占位）
- **邮箱密码页**：`LoginEmailPassword`
  - 密码可见/不可见切换，登录按钮仅做占位（未触发真实登录）
- **登录鉴权/加载态**：`LoginAuth`
  - Canvas 粒子/圆环背景 + 进度条动画（当前结束仅 `print`，未回调路由）
- **首页**：`HomeView` 仍为模板占位


## 目录结构
imate_ios_app/ ├── README.md ├── imate.xcodeproj/ │ └── project.pbxproj └── imate/ ├── imateApp.swift # @main 入口 ├── Entrance.swift # NavigationStack + navigationDestination + 注入 Router ├── router/ │ └── AppRoute.swift # AppRoute + Router(push/pop/popToRoot) ├── login/ │ ├── Login.swift # 登录主页面 │ ├── components/ │ │ └── LoginWidgets.swift # 登录页子组件（背景、文案、按钮、条款） │ └── view/ │ ├── LoginEmail.swift │ ├── LoginEmailPassword.swift │ └── LoginAuth.swift ├── home/ │ └── HomeView.swift # 占位首页 ├── common/ │ └── ColorExtension.swift # Color(hex:) / Color(hex:alpha:) └── Assets.xcassets/ # AppIcon、AccentColor、login/logo 等


## 资源与注意事项

- 工程中多处使用 `Image("logo")`：
  - 需要在 `Assets.xcassets` 中存在名为 `logo` 的图片资源（当前仓库内有 `Assets.xcassets/login/logo.imageset/logo.svg`）。

## 依赖与测试

- **Swift Package / CocoaPods**：当前工程未声明 SPM 产品依赖（`packageProductDependencies` 为空），也未见 `Podfile` 等依赖管理文件。
- **单元测试 / UI 测试**：本目录内未见测试 target 源码。

## 本地运行

1. 使用 Xcode 打开 `imate.xcodeproj`
2. 选择 `imate` scheme
3. 在模拟器或真机运行

## 下一步建议（按现状最短路径）

- 接入真实的 Apple 登录 / 邮箱登录与后端会话，统一登录成功后的路由落点（例如 `router.push(.home)` 或替换根路由）
- 把 `LoginEmail` / `LoginEmailPassword` 的占位参数（如 email 常量）改为真实状态传递
- 为 `LoginAuth` 动画完成后的行为补齐：成功进入首页、失败提示与重试
- 建立最小测试（路由与输入校验）并补充 CI（如有需要）