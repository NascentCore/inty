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
  color: @primary-color;        // 使用主题色
  padding: @spacing-lg;          // 使用间距变量
  font-size: @font-size-base;    // 使用字体大小变量
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