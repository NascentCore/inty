# IntelliMate

面向年轻人的长期 AI 陪伴应用

## 📋 项目简介

IntelliMate 是一款专为年轻人打造的长期 AI 陪伴应用，主打**亲密角色扮演**功能。用户可以与 AI 角色进行深度互动，创建属于自己的专属 IntelliMate——一个能够理解你、陪伴你、与你共同成长的 AI 伙伴。

### 🎯 核心功能

- 🤖 **AI 角色扮演** - 与多样化的 AI 角色进行亲密互动
- 💬 **智能对话** - 自然流畅的对话体验，深度理解用户情感
- 🎭 **个性化定制** - 创建和培养专属于你的 IntelliMate
- 📱 **跨平台支持** - 随时随地与你的 AI 伙伴保持连接
- 🔒 **隐私保护** - 用户数据安全加密，保护个人隐私

### ✨ 特性

- 🚀 **React 19** - 最新版本的 React
- 💎 **TypeScript** - 完整的类型支持
- 📦 **UmiJS 4** - 可扩展的企业级前端应用框架
- 🔧 **Biome** - 快速的代码检查和格式化工具
- 🎯 **规范化** - 统一的代码规范和 Git 提交规范
- 📱 **响应式** - 支持移动端和桌面端

---

## 🚀 快速开始

### 环境要求

- Node.js >= 20.0.0
- yarn（项目统一使用 yarn 作为包管理器）

### 安装依赖

```bash
yarn
```

### 启动开发服务器

```bash
npm run dev
# 或
npm start
```

访问 [http://localhost:8000](http://localhost:8000) 查看应用。

### 构建生产版本

```bash
npm run build
```

构建产物将生成在 `dist` 目录下。

### 代码检查

```bash
# 运行 lint 检查
npm run lint

# TypeScript 类型检查
npm run tsc
```

---

## 📁 项目结构

```
intellimate/
├── src/
│   ├── components/      # 公共组件
│   ├── pages/          # 页面组件
│   ├── layouts/        # 布局组件
│   ├── constants/      # 常量定义
│   ├── types/          # TypeScript 类型定义
│   ├── utils/          # 工具函数
│   ├── styles/         # 全局样式
│   ├── hooks/          # 自定义 Hooks
│   ├── services/       # API 服务
│   ├── models/         # 数据模型（useModel）
│   └── locales/        # 国际化文件
├── config/             # UmiJS 配置（路由、代理等）
├── docs/              # 项目文档
└── public/            # 静态资源
```

---

## 🛠️ 技术栈

- **框架**: React 19 + UmiJS 4
- **语言**: TypeScript 5.6+
- **UI 实现**: 原生 HTML + Less（不使用 UI 组件库）
- **图标库**: lucide-react
- **样式**: Less
- **状态管理**: UmiJS useModel
- **SDK**: Inty TypeScript SDK（自研 AI 聊天 SDK）
- **代码检查**: Biome
- **Git Hooks**: Husky + Commitlint
- **包管理器**: Yarn

---

## 🧭 架构概览

- **框架与构建**: 基于 React 19 + UmiJS 4，`config/config.ts` 启用 umi-presets-pro、hash 构建、moment2dayjs、mako，并在构建时注入 `BUILD_TIME`。
- **状态模型**: `useModel` 驱动的 `chat`、`agent`、`chatList`、`user`、`googleLoginModal` 负责懒加载、分页管理与错误重置。
- **API 客户端**: `utils/intyClient.ts` 统一创建 Inty SDK 实例，`services/*` 通过 `client.api.v1` 访问推荐、消息、语音、用户等接口。
- **本地设施**: `utils/storage.ts` 抽象 IndexedDB，本地保存 token 与设备 ID；`utils/logger.ts` 在开发期输出调试日志。

---

## 🗺️ 页面与路由

- **侧边栏布局**: `SidebarLayout` 首次挂载时拉取聊天列表与用户档案，内置 Discover 与订阅入口，并全局挂载 `GoogleLoginModal` 与 `VersionBadge`。
- **首页推荐**: `/` 调用 `useModel('agent')` 的 `loadRecommendAgents` 渲染角色卡片，并将“Start chat”跳转到 `/chat/:agentId`。
- **聊天体验**: `ChatPage` 根据路由参数加载 Agent 详情与历史消息，乐观追加用户消息并在 `MessageSendError` 时回滚。
- **个人中心**: `/profile` 根据 `isRegistered` 决定展示登录面板或 `ProfileHeader/BasicInfo/AccountInfo` 组合，并支持快速退出登录。
- **其他路由**: `/subscribe` 引导会员升级，`/dev-test` 聚合 SDK 功能调试，`/*` 统一落入 `NotFound`。

---

## 🔊 语音与多媒体

- **语音播放**: `useVoicePlayer` 负责语音生成、缓存与播放，登录缺失时触发 `googleLoginModal.show()`。
- **消息组件**: `MessageItem` 在 AI 气泡上提供播放/停止按钮，调用 `generateMessageVoice` 获取音频并显示 `Loader2` 状态。
- **列表体验**: `MessageList` 自动滚动定位、显示发送中占位，并在空数据时渲染骨架状态。
- **首屏加载**: `public/scripts/loading.js` 与 `global.tsx` 处理白屏占位与 PWA 缓存清理，保持加载体验稳定。

---

## 🔐 认证与登录

- **访客模式**: `src/app.tsx` 的 `getInitialState` 在缺少 Token 时调用 `guestLogin`，依赖 `getOrCreateDeviceId` 生成设备 ID，并通过 `services/auth.guestLogin` 写入访客凭证。
- **Google 登录**: `components/GoogleLoginModal` 基于 `@react-oauth/google` 登录主账号，完成后刷新聊天列表与用户资料并重定向首页。
- **Token 管理**: `utils/token.ts` 暴露 `getToken/saveToken/hasToken`，`createIntyClient(true)` 在缺少凭证时直接抛错。
- **设备标识**: `utils/device.ts` 负责生成、缓存、重置设备 ID，确保访客登录参数一致。

---

## 🌍 国际化与样式

- **双语资源**: `src/locales` 下维护 `zh-CN` 与 `en-US` 文案，`config/config.ts` 启用 `locale` 插件自动读取浏览器语言。
- **样式体系**: 项目采用 Less，`styles/variables.less` 集中主题变量，`global.less` + `reset.less` 统一基础样式。
- **布局常量**: `constants/index.ts` 定义布局尺寸、主题色、断点以及 `INTY_SDK_CONFIG` 基础参数。
- **图标与字体**: 通过 `lucide-react` 与 `styles/fonts.less` 提供统一视觉，同时 `components/Icon` 包装 Icon 渲染。

---

## 🧪 开发与测试支持

- **DevTest 工具台**: `/dev-test` 目录按功能拆分游客登录、用户、推荐、聊天、语音等测试组件，并在 `README.md` 详解用法。
- **日志调试**: `utils/logger.ts` 提供 `test/testSuccess/testError` 等方法，DevTest 组件统一使用便于 QA 追踪。
- **错误收敛**: `utils/testError.ts` 将 SDK 异常映射为友好的错误类型并支持统一处理。
- **版本标记**: `components/VersionBadge` 显示构建时间，`config/config.ts` 的 `requestRecord`、`metas` 等设置辅助排查缓存与网络。

---

## 📖 开发指南

### 代码规范

项目遵循统一的代码规范。

**核心规范：**

- 所有接口名称以大写字母 `I` 开头（如 `IUserInfo`）
- 禁止使用 `any` 类型
- 使用 `@/` 别名导入项目模块
- 常量统一在 `src/constants/` 中管理
- 样式变量统一在 `src/styles/variables.less` 中定义

### Git 提交规范

项目使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```bash
# 新功能
git commit -m "feat: 添加用户登录功能"

# Bug 修复
git commit -m "fix: 修复导航栏样式问题"

# 文档更新
git commit -m "docs: 更新 README 文档"

# 重构
git commit -m "refactor: 重构用户模块代码"
```

### 样式开发

项目已统一样式管理，使用 Less 变量：

```less
// 在组件样式文件中导入变量
@import '@/styles/variables.less';

.my-component {
  color: @primary-color; // 使用主题色
  padding: @spacing-lg; // 使用间距变量
  font-size: @font-size-base; // 使用字体大小变量
}
```

可用的样式变量请查看 `src/styles/variables.less`。

---

## 📚 文档

- [Inty SDK 文档](./docs/README.md) - Inty TypeScript SDK 使用指南
- [API 文档](./docs/api/) - API 接口文档

## 📄 License

[MIT](./LICENSE)

---

## 🙏 致谢

- [UmiJS](https://umijs.org/)
- [React](https://react.dev/)
