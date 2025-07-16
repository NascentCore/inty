# 项目结构

## 📁 目录概览

```
inty-app/
├── 📱 app/                          # 主应用模块
│   ├── src/main/java/com/ai/inty/   # Kotlin 源代码
│   │   ├── 💬 chat/                 # 聊天功能
│   │   │   └── ChatPage.kt          # 聊天 UI 组件
│   │   ├── 🏠 home/                 # 主页屏幕
│   │   │   ├── HomePage.kt          # 主页界面
│   │   │   └── RecommendPage.kt     # 角色推荐
│   │   ├── 📊 beans/                # 数据模型
│   │   │   ├── AgentInfo.kt         # AI 角色数据
│   │   │   ├── MsgInfo.kt           # 消息模型
│   │   │   └── UserProfile.kt       # 用户数据模型
│   │   ├── 🌐 net/                  # API 接口
│   │   │   ├── IAgentApi.kt         # 角色 API
│   │   │   ├── IChatApi.kt          # 聊天 API
│   │   │   └── IUserApi.kt          # 用户 API
│   │   ├── 🎯 viewmodels/           # MVVM ViewModels
│   │   │   ├── ChatViewModel.kt     # 聊天逻辑
│   │   │   ├── MainViewModel.kt     # 主屏幕逻辑
│   │   │   └── ReportViewModel.kt   # 报告功能
│   │   ├── 🔧 base/                 # 基础组件
│   │   │   ├── BaseActivity.kt      # 基础 Activity 类
│   │   │   └── IntyImage.kt         # 自定义图像组件
│   │   ├── 📱 Activities            # 屏幕活动
│   │   │   ├── SplashActivity.kt    # 应用启动
│   │   │   ├── MainActivity.kt      # 主界面
│   │   │   ├── ChatActivity.kt      # 个人聊天
│   │   │   ├── LoginActivity.kt     # 身份验证
│   │   │   ├── CreateRoleActivity.kt # 角色创建
│   │   │   └── AvatarGenerateActivity.kt # AI 头像生成
│   │   └── 🎨 ui/theme/             # UI 主题
│   │       ├── Color.kt             # 颜色定义
│   │       └── Theme.kt             # Material3 主题
│   ├── src/main/res/                # Android 资源
│   │   ├── drawable/                # 图片和图标
│   │   ├── values/                  # 字符串、颜色、样式
│   │   └── xml/                     # 配置文件
│   ├── google-services.json         # Firebase 配置
│   └── build.gradle.kts             # 应用构建配置
│
├── 🌐 network/                      # 网络模块
│   ├── src/main/java/               # 网络层代码
│   │   ├── HttpResult.kt            # 响应包装器
│   │   └── NetworkInterceptors.kt   # HTTP 拦截器
│   └── build.gradle.kts             # 网络模块配置
│
├── 🔧 utils/                        # 工具模块
│   ├── src/main/java/               # 工具类
│   │   ├── log/EasyLog.kt           # 日志系统
│   │   ├── storage/IntySetting.kt   # 设置存储
│   │   └── env/ProcessUtils.kt      # 系统工具
│   └── build.gradle.kts             # 工具模块配置
│
├── 🔐 sign/                         # 密钥库文件
│   ├── key.jks                      # 调试密钥库
│   └── my-release-key.jks           # 发布密钥库
│
├── 📋 配置文件
│   ├── keystore.properties          # 签名配置
│   ├── keystore.properties.template # 配置模板
│   ├── local.properties             # SDK 路径
│   ├── gradle.properties            # Gradle 设置
│   └── settings.gradle.kts          # 项目设置
│
├── 📚 文档
│   ├── README.md                    # 主项目文档
│   ├── CONTRIBUTING.md              # 开发指南
│   ├── CHANGELOG.md                 # 版本历史
│   ├── LICENSE                      # MIT 许可证
│   ├── CLAUDE.md                    # 开发说明
│   ├── data_safety_declaration.md   # Play Store 合规
│   └── play_app_signing_guide.md    # 签名设置指南
│
├── 🔧 构建系统
│   ├── build.gradle.kts             # 根构建配置
│   ├── gradle/                      # Gradle 包装器
│   ├── gradlew                      # Gradle 包装器脚本
│   └── libs.versions.toml           # 版本目录
│
└── 🚫 忽略文件 (.gitignore)
    ├── /build/                      # 构建输出
    ├── /.idea/                      # IDE 文件
    ├── keystore.properties          # 签名密钥
    └── local.properties             # 本地 SDK 路径
```

## 🏗️ 架构层次

### 表示层 (UI)
- **Jetpack Compose** 用于 UI 组件
- **Material3** 设计系统
- **Activities** 用于屏幕容器
- **ViewModels** 用于 UI 状态管理

### 业务逻辑层
- **ViewModels** 包含业务规则
- **用例** (在 ViewModels 中隐含)
- **状态管理** 使用 StateFlow

### 数据层
- **Repository 模式** (在 ViewModels 中隐含)
- **API 服务** 用于网络数据
- **本地存储** 使用 MMKV
- **数据模型** 在 beans 包中

### 基础设施层
- **网络模块** 用于 HTTP 通信
- **工具模块** 用于横切关注点
- **日志系统** 用于调试
- **导航** 使用 TheRouter

## 📱 关键组件

### 核心 Activities 流程
```
SplashActivity → MainActivity ↔ ChatActivity
                      ↓
              LoginActivity (如需要)
                      ↓
              其他 Activities (设置、创建等)
```

### 数据流
```
UI (Compose) → ViewModel → API Service → Network Module → Backend
     ↑                              ↓
StateFlow ← Repository ← Local Storage (MMKV)
```

### 导航模式
```
TheRouter.build(Constant.ROUTE_CHAT)
    .withString("agentId", "123")
    .navigation(context)
```

## 🔧 模块依赖

```
app
├── 依赖于 → network
├── 依赖于 → utils
└── 实现 → 所有 UI 和业务逻辑

network
├── 独立模块
└── 提供 → HTTP 抽象

utils
├── 独立模块  
└── 提供 → 日志、存储、工具
```

## 📦 构建变体

### 调试构建
- **包名**: `com.ai.inty`
- **签名**: 调试密钥库
- **功能**: Chucker、扩展日志
- **版本**: 包含 git 提交哈希

### 发布构建
- **包名**: `com.ai.inty`
- **签名**: 发布密钥库
- **功能**: 混淆、优化
- **版本**: 清洁版本号

## 🗂️ 资源组织

### Drawable 资源
- 应用图标和标志
- UI 图标和按钮
- 背景图像
- 用于可扩展性的矢量图

### 字符串资源
- 多语言支持
- 功能特定字符串组
- 错误消息和验证文本

### 颜色和主题资源
- Material3 配色方案
- 自定义品牌颜色
- 深色/浅色主题支持