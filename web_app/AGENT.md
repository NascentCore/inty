# AGENT.md

## 项目概述

IntelliMate 是一个面向年轻人的长期 AI 陪伴应用，主打亲密角色扮演功能。使用 React 19 + TypeScript + UmiJS 4 构建，**不使用任何第三方 UI 组件库**，全部界面使用原生 HTML + CSS + Less 实现。

## 常用命令

```bash
# 安装 Inty SDK（首次安装时需要）
cd evaluation/inty_sdk && yarn install --frozen-lockfile && yarn build && cd ../..

# 安装项目依赖
yarn

# 启动开发服务器（端口 6600）
npm run dev
# 或
npm start

# 代码格式化
npm run format

# 代码检查（Biome Lint + TypeScript）
npm run lint

# 仅 TypeScript 类型检查
npm run tsc

# 构建生产版本
npm run build

# 分析构建产物
npm run analyze
```

## 关键架构

### 目录结构

```
src/
├── components/      # 通用组件
├── pages/          # 页面组件（路由对应）
├── layouts/        # 布局组件
├── models/         # UmiJS useModel 状态管理
├── services/       # API 服务层（已废弃，改用 http/api/）
├── http/           # HTTP 工具（request、interceptors、types）
├── utils/          # 工具函数（intyClient、token、storage、logger）
├── hooks/          # 自定义 Hooks
├── types/          # 全局 TypeScript 类型定义
├── constants/      # 常量配置
├── styles/         # 全局样式（variables.less、global.less）
└── locales/        # 国际化文件
```

### 状态管理：useModel

使用 UmiJS 内置的 `useModel` 进行状态管理，主要模型：

- **agent.ts** - AI 代理管理（推荐列表、详情、搜索）
- **chat.ts** - 聊天状态（消息列表、发送状态、分页）
- **chatList.ts** - 聊天列表管理
- **user.ts** - 用户信息管理
- **googleLoginModal.ts** - Google 登录模态框状态

```typescript
// 在组件中使用
const { messages, sendChatMessage } = useModel('chat');
```

### API 调用架构

**新架构（推荐）：**
- `src/http/api/*.ts` - API 请求方法
- `src/http/types/*.ts` - 对应的类型声明

**旧架构（仍在使用）：**
- `src/services/*.ts` - 基于 Inty SDK 的服务封装

```typescript
// 新方式
import { getChatMessages, clearMessages } from '@/http/api/chat';

// 旧方式（Inty SDK）
import { sendMessage } from '@/services/chat';
```

### Inty SDK 客户端

`src/utils/intyClient.ts` 统一创建 SDK 实例：

```typescript
import { createIntyClient } from '@/utils';

// 无需认证
const client = await createIntyClient();

// 需要认证
const client = await createIntyClient(true);
```

### 认证机制

- **访客模式**：自动生成设备 ID，无需登录即可使用
- **Google OAuth**：完整用户账户体系
- **Token 存储**：基于 IndexedDB（`src/utils/storage.ts`）

## 编码规范

### TypeScript

- **接口命名必须以 `I` 开头**：`IUserInfo`、`IChatMessage`
- **禁止使用 `any` 类型**
- **使用 `@/` 别名**导入项目模块

### 组件规范

- **函数式组件 + Hooks**
- **组件目录结构**：
  ```
  ComponentName/
  ├── index.tsx
  └── index.less
  ```
- **Props 必须定义接口类型**

### 样式规范

- **使用 Less**，样式结构必须严格对应 JSX DOM 层级
- **样式变量**统一在 `src/styles/variables.less` 定义
- **外层容器 class**必须唯一且具有描述性
- **禁止使用 Ant Design**，全部 UI 使用原生 HTML 元素

### 命名规范

- **变量/函数**：小驼峰 `camelCase`
- **组件**：大驼峰 `PascalCase`
- **常量**：全大写下划线 `UPPER_SNAKE_CASE`
- **接口**：大写 `I` 开头 + 大驼峰 `IUserInfo`

### 注释规范

- **每个文件顶部**必须包含文件说明
- **导出函数**必须包含 JSDoc
- **接口和复杂类型**需要添加注释

## 特殊注意事项

### Inty SDK 安装

首次克隆项目后，需要先构建 Inty SDK：

```bash
cd evaluation/inty_sdk
yarn install --frozen-lockfile
yarn build
cd ../..
```

SDK 以本地包形式引入：`"inty": "file:../evaluation/inty_sdk"`

### 开发测试页面

`/dev-test` 路由提供了完整的 SDK 功能测试界面，方便调试各种 API。

### 语音播放

`src/hooks/useVoicePlayer.ts` 管理语音生成、缓存与播放。未登录时会自动触发 Google 登录。

### 国际化

项目支持中英双语，配置在 `src/locales/` 目录。
