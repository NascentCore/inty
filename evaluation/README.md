# InTy 智能体评测系统前端

## 📖 系统概述

InTy 智能体评测系统前端是基于 React + TypeScript + Vite 构建的现代化Web应用，用于全面评测智能体的对话质量、角色一致性和表达能力。支持容器化部署，可独立运行并连接远程后端服务。

Insert the following record to the backend DB to allow this app to use `user-01JWZ34Y4D1C92GD86A5R6EWYJ`
to talk to the backend.

### 使用本地 Inty 后端地址

在本代码库顶层目录，运行 `docker compose up --build` 来启动本地后端，
启动后，后端地址位于 `http://localhost:8000/api/v1`，该地址要填入 Inty-eval 所使用的后端地址。

然后，需要向 Inty 后端数据库内写入预置的用户信息，以便让 inty-eval 可以通过内置的用户名来访问本地 inty 后端。
登录后端数据库：`docker exec -it inty-backend-pgvector-1 psql -U postgres -d inty`
然后运行以下 SQL 指令

```psql
INSERT INTO users (
    id,
    nickname,
    avatar,
    email,
    phone,
    gender,
    age_group,
    description,
    auth_type,
    system_language,
    is_active,
    created_at,
    updated_at,
    device_id,
    google_id,
    is_superuser,
    readable_id,
    deleted_at,
    anonymized_at,
    deletion_reason
) VALUES (
    'user-01JWZ34Y4D1C92GD86A5R6EWYJ',
    'dx',
    NULL,
    'test@examle.com',
    NULL,
    'MALE',
    '18-24',
    NULL,
    'GOOGLE',
    'zh',
    true,
    '2025-06-05 03:46:24.001931+00',
    '2025-07-18 02:09:05.645221+00',
    NULL,
    'deleted_google_b5ebf227',
    true,
    '10000001',  -- Changed to a unique value
    NULL,
    '2025-07-18 02:09:10.275081+00',
    '隐私关注'
);
```

然后，将 inty-eval 指向后端地址，即可调用。上面创建的用户，其 jwt token 已经写死在
inty-eval 代码中。位于 `getAuthToken()`。

```bash
# 先将环境变量指定为本地 Inty 后端地址
export REACT_APP_API_BASE_URL=http://localhost:8000/api/v1

# 启动 inty-eval 服务；打开 http://localhost:3000
npm run dev
```

### 🎯 核心特性

- ✅ **现代化技术栈** - React 18 + TypeScript + Vite + Ant Design 5
- ✅ **容器化部署** - 支持Docker容器独立部署
- ✅ **环境变量配置** - 灵活的API地址配置，支持本地和远程后端
- ✅ **多智能体评测** - 支持批量选择和并行评测多个智能体
- ✅ **实时监控界面** - WebSocket实时监控评测进度
- ✅ **智能体管理** - 完整的智能体CRUD操作界面
- ✅ **聊天功能** - 支持与智能体进行实时对话测试
- ✅ **问题管理** - 支持手动添加、批量导入、模板管理
- ✅ **评测历史** - 查看历史评测记录和结果分析
- ✅ **Prompt查询** - 智能体提示词查询和管理工具

## 🏗️ 技术架构

### 前端技术栈

```
React 18                    # 用户界面库
├── TypeScript              # 类型安全的JavaScript超集
├── Vite                    # 快速的构建工具和开发服务器
├── Ant Design 5            # 企业级UI组件库
├── @ant-design/icons       # 丰富的图标组件
└── Docker                  # 容器化部署
```

### 项目结构

```
app/static/evaluation/
├── components/                   # React组件库
│   ├── auth/                    # 认证相关组件
│   │   ├── AuthProvider.tsx    # 认证上下文提供者
│   │   └── AuthStatus.tsx      # 认证状态显示
│   ├── evaluation/              # 评测功能组件
│   │   ├── TestConfigForm.tsx   # 评测配置表单
│   │   ├── AgentSelector.tsx    # 智能体选择器
│   │   ├── QuestionManager.tsx  # 问题管理器
│   │   ├── MultiAgentChatDisplay.tsx # 多智能体对话展示
│   │   └── EvaluationMonitor.tsx # 实时评测监控
│   └── common/                  # 通用组件
├── pages/                       # 页面级组件
│   ├── EvaluationPage.tsx      # 评测创建和管理主页面
│   ├── EvaluationHistoryPage.tsx # 评测历史记录页面
│   ├── ChatPage.tsx            # 智能体聊天页面
│   ├── AgentManagePage.tsx     # 智能体管理页面
│   └── PromptQueryPage.tsx     # Prompt查询页面
├── hooks/                       # React自定义Hooks
│   ├── useAgents.ts            # 智能体数据管理Hook
│   ├── useEvaluationSession.ts # 评测会话管理Hook
│   └── useForm.ts              # 表单状态管理Hook
├── services/                    # API服务层
│   ├── api.ts                  # 统一API客户端
│   ├── auth.ts                 # 认证服务
│   └── modelCache.ts           # 模型缓存服务
├── types/                       # TypeScript类型定义
│   └── index.ts                # 全局类型定义
├── styles/                      # 样式文件
│   └── index.css               # 全局样式
├── utils/                       # 工具函数库
├── Dockerfile                   # Docker构建文件
├── vite.config.ts              # Vite配置文件
├── tsconfig.json               # TypeScript配置
├── package.json                # 项目依赖和脚本
└── nginx.conf                  # Nginx配置文件
```

## 🔧 环境要求

### 开发环境

- Node.js 18+ (用于本地开发和构建)
- npm 或 yarn (包管理器)
- Modern Web Browser (Chrome 90+, Firefox 88+, Safari 14+)

### 生产环境

- Docker (用于容器化部署)
- 远程后端API服务 (如: <https://dev.inty.sxwl.ai>)

## 🚀 快速开始

### 方式一：本地开发模式

1. **安装依赖**

```bash
cd app/static/evaluation
npm install
```

2. **配置环境变量**

```bash
# 创建环境变量文件
echo "REACT_APP_API_BASE_URL=https://dev.inty.sxwl.ai/api/v1" > .env
```

3. **启动开发服务器**

```bash
npm run dev
```

4. **访问应用**
打开浏览器访问: `http://localhost:3000`

### 方式二：Docker容器部署

1. **构建Docker镜像**

```bash
# 构建并配置API地址
docker build \
  --build-arg REACT_APP_API_BASE_URL=https://dev.inty.sxwl.ai/api/v1 \
  -t inty-frontend:latest .
```

2. **运行容器**

```bash
docker run -d -p 3000:80 --name inty-frontend inty-frontend:latest
```

3. **访问应用**
打开浏览器访问: `http://localhost:3000`

### 方式三：快速部署脚本

使用提供的部署脚本：

```bash
# 开发环境快速启动
./dev.sh

# 生产环境构建和部署
./deploy.sh

# 构建多架构镜像
./build-multi-arch.sh
```

## 📋 API 端点

### 评测会话管理

- `POST /api/v1/evaluation/sessions` - 创建评测会话
- `GET /api/v1/evaluation/sessions` - 获取会话列表
- `GET /api/v1/evaluation/sessions/{id}` - 获取会话详情
- `POST /api/v1/evaluation/sessions/{id}/start` - 启动评测
- `POST /api/v1/evaluation/sessions/{id}/cancel` - 取消评测
- `GET /api/v1/evaluation/sessions/{id}/results` - 获取评测结果

### 智能体管理

- `GET /api/v1/ai/agents/` - 获取智能体列表
- `GET /api/v1/ai/agents/{id}` - 获取智能体详情
- `GET /api/v1/ai/agents/recommend` - 获取推荐智能体
- `GET /api/v1/ai/agents/search` - 搜索智能体
- `POST /api/v1/ai/agents/` - 创建智能体
- `PUT /api/v1/ai/agents/{id}` - 更新智能体

### 聊天功能

- `POST /api/v1/chats/agents/{id}/chat/completions` - 发送消息 (OpenAI格式)
- `POST /api/v1/chats/agents/{id}/chat/fast` - 快速聊天接口
- `GET /api/v1/chats/agents/{id}/detail` - 获取聊天详情
- `POST /api/v1/chats/agents/{id}/clear-messages` - 清除消息

### 认证管理

- `POST /api/v1/auth/guest` - 创建游客用户
- `GET /api/v1/auth/profile` - 获取用户信息

### 模型管理

- `GET /api/v1/ai/models/openrouter` - 获取可用模型列表

### 实时监控

- `WSS /api/v1/evaluation/sessions/{id}/monitor` - WebSocket监控

## 🎮 功能模块使用指南

### 1. 智能体评测模块

**创建评测会话流程：**

1. **基础配置**
   - 设置评测会话名称和描述
   - 选择评分模型 (支持多种LLM模型)
   - 配置评分标准和权重
   - 设置用户身份类型和模拟场景

2. **智能体选择**
   - 从智能体库中浏览可用智能体
   - 支持多选批量评测
   - 实时搜索和标签过滤
   - 查看智能体详细信息和配置

3. **测试问题管理**
   - 手动添加单个测试问题
   - 批量导入问题文件 (.txt, .csv, .json)
   - 选择和编辑预设问题模板
   - 动态调整问题顺序和分组

4. **执行评测**
   - 一键启动多智能体并行评测
   - 实时监控评测进度和状态
   - 查看评测过程中的对话内容
   - 自动生成评测报告和统计数据

### 2. 智能体聊天模块

**单智能体对话功能：**

- 选择任意智能体进行实时对话
- 支持流式和非流式聊天模式
- 查看完整聊天历史记录
- 一键清除会话记录
- 导出聊天记录为JSON/CSV格式

### 3. 智能体管理模块

**智能体CRUD操作：**

- 查看所有可用智能体列表
- 创建新的智能体配置
- 编辑现有智能体的属性和提示词
- 管理智能体的可见性和权限
- 复制和备份智能体配置

### 4. 评测历史模块

**历史记录管理：**

- 查看所有历史评测会话
- 按时间、状态、评分等条件筛选
- 详细查看评测结果和统计信息
- 对比不同评测会话的结果
- 导出历史数据和报告

### 5. Prompt查询模块

**提示词管理工具：**

- 搜索和查看智能体的系统提示词
- 分析提示词的结构和特点
- 比较不同智能体的提示词差异
- 优化和调试提示词效果

## 🔍 核心设计原则

### 1. 现代化前端架构

- **组件化设计**: 高度模块化的React组件，易于维护和复用
- **类型安全**: 完整的TypeScript类型定义，减少运行时错误
- **状态管理**: 使用React Hooks进行状态管理，代码更简洁
- **API抽象**: 统一的API客户端，支持错误处理和类型转换

### 2. 容器化部署

- **环境变量配置**: 支持构建时和运行时环境变量配置
- **多阶段构建**: Docker多阶段构建优化镜像大小
- **Nginx代理**: 生产环境使用Nginx提供静态文件服务
- **健康检查**: 内置容器健康检查机制

### 3. 开发体验优化

- **热重载**: Vite提供快速的开发服务器和热重载
- **代码规范**: ESLint + TypeScript确保代码质量
- **构建优化**: 生产构建自动优化和压缩
- **源码映射**: 支持生产环境调试

### 4. 用户体验设计

- **响应式布局**: 适配不同屏幕尺寸的设备
- **实时反馈**: WebSocket实时更新和加载状态提示
- **错误处理**: 友好的错误提示和异常处理
- **性能优化**: 组件懒加载和渲染优化

## 🧪 开发和调试

### 本地开发调试

1. **启动开发服务器**

```bash
npm run dev
# 访问 http://localhost:3000
```

2. **类型检查**

```bash
npm run type-check
```

3. **代码规范检查**

```bash
npm run lint
```

### 生产构建测试

1. **构建生产版本**

```bash
npm run build
```

2. **预览构建结果**

```bash
npm run preview
# 访问 http://localhost:4173
```

### API连通性测试

1. **检查后端API状态**

```bash
# 测试智能体API
curl "https://dev.inty.sxwl.ai/api/v1/ai/agents/?limit=10"

# 测试评测API
curl "https://dev.inty.sxwl.ai/api/v1/evaluation/sessions"
```

2. **使用测试页面**

```bash
# 访问API测试页面
open test-api-fix.html
open test-frontend.html
```

### Docker容器调试

1. **查看容器日志**

```bash
docker logs inty-frontend --tail 50 -f
```

2. **进入容器调试**

```bash
docker exec -it inty-frontend sh
```

3. **检查容器健康状态**

```bash
docker inspect inty-frontend | grep -A 10 Health
```

## 📊 监控和性能

### 评测会话状态

- `PENDING` - 等待启动
- `RUNNING` - 正在执行
- `COMPLETED` - 已完成
- `FAILED` - 执行失败
- `CANCELLED` - 已取消

### 性能指标

- 响应时间统计
- 成功率分析
- 智能体性能对比
- 评分分布统计

## ⚙️ 配置选项

### 环境变量配置

1. **构建时环境变量**

```bash
# Dockerfile中的ARG参数
ARG REACT_APP_API_BASE_URL=https://dev.inty.sxwl.ai/api/v1
ARG REACT_APP_ENV=production
```

2. **开发环境变量**

```bash
# .env文件
REACT_APP_API_BASE_URL=https://dev.inty.sxwl.ai/api/v1
REACT_APP_ENV=development
```

### Vite配置 (vite.config.ts)

```typescript
export default defineConfig({
  // 环境变量配置
  define: {
    'process.env.REACT_APP_API_BASE_URL': JSON.stringify(process.env.REACT_APP_API_BASE_URL)
  },
  
  // 开发服务器配置
  server: {
    port: 3000,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      }
    }
  }
});
```

### Docker配置

1. **多阶段构建配置**

```dockerfile
# 构建阶段
FROM node:18-alpine AS builder
ARG REACT_APP_API_BASE_URL
ENV REACT_APP_API_BASE_URL=$REACT_APP_API_BASE_URL

# 生产阶段
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

2. **Nginx配置 (nginx.conf)**

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;
    
    # 健康检查端点
    location /health {
        return 200 'OK';
    }
    
    # SPA路由支持
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## 🚨 故障排除

### 常见问题及解决方案

1. **API请求404错误**

   ```bash
   # 问题：前端请求API返回404
   # 原因：API地址配置错误或后端服务未启动
   
   # 解决方案：
   # 1. 检查环境变量配置
   docker exec inty-frontend env | grep REACT_APP
   
   # 2. 验证API地址是否正确编译到JS中
   docker exec inty-frontend grep -o "https://dev\.inty\.sxwl\.ai" /usr/share/nginx/html/assets/*.js
   
   # 3. 测试后端API是否可访问
   curl "https://dev.inty.sxwl.ai/api/v1/ai/agents/?limit=1"
   ```

2. **Docker构建失败**

   ```bash
   # 问题：构建时环境变量未生效
   # 原因：ARG和ENV配置不正确
   
   # 解决方案：
   # 1. 确认Dockerfile中有ARG声明
   # 2. 确认vite.config.ts中有define配置
   # 3. 重新构建时明确指定参数
   docker build --build-arg REACT_APP_API_BASE_URL=https://dev.inty.sxwl.ai/api/v1 -t inty-frontend .
   ```

3. **前端页面空白或加载失败**

   ```bash
   # 问题：页面无法正常显示
   # 原因：静态资源路径错误或nginx配置问题
   
   # 解决方案：
   # 1. 检查nginx配置
   docker exec inty-frontend cat /etc/nginx/conf.d/default.conf
   
   # 2. 检查静态文件是否存在
   docker exec inty-frontend ls -la /usr/share/nginx/html/
   
   # 3. 查看nginx错误日志
   docker logs inty-frontend 2>&1 | grep error
   ```

4. **CORS跨域错误**

   ```bash
   # 问题：浏览器提示跨域错误
   # 原因：后端未配置允许前端域名的CORS
   
   # 解决方案：
   # 在后端config.yaml中添加前端域名：
   # backend_cors_origins: ["http://localhost:3000", "https://你的域名"]
   ```

### 调试工具和命令

1. **前端调试**

```bash
# 查看构建产物
npm run build && ls -la dist/

# 本地预览生产构建
npm run preview

# 检查TypeScript类型
npm run type-check
```

2. **容器调试**

```bash
# 查看容器内部文件
docker exec inty-frontend find /usr/share/nginx/html -name "*.js" | head -5

# 检查nginx进程状态
docker exec inty-frontend ps aux | grep nginx

# 测试容器健康检查
docker exec inty-frontend curl -f http://localhost/health
```

3. **网络调试**

```bash
# 从容器内测试API连通性
docker exec inty-frontend wget -qO- https://dev.inty.sxwl.ai/api/v1/ai/agents/

# 检查DNS解析
docker exec inty-frontend nslookup dev.inty.sxwl.ai
```

## 📈 发展路线图

### 已完成功能 ✅

- [x] React + TypeScript + Vite 现代化前端架构
- [x] Docker容器化部署支持
- [x] 环境变量配置和多环境支持
- [x] 智能体管理和CRUD操作界面
- [x] 实时聊天功能和历史记录
- [x] 评测会话创建和管理
- [x] 多智能体并行评测
- [x] 实时评测监控和进度展示
- [x] Prompt查询和管理工具
- [x] 响应式UI设计和用户体验优化

### 计划中功能 🚧

- [ ] **流式评测结果** - 支持流式显示评测进度和结果
- [ ] **语音评测集成** - 集成语音合成和识别功能
- [ ] **智能体性能分析** - 详细的性能指标和统计分析
- [ ] **A/B测试功能** - 支持不同版本智能体的对比测试
- [ ] **自定义评测模板** - 用户可创建和共享评测模板
- [ ] **批量操作优化** - 支持批量导入、导出和操作
- [ ] **移动端适配** - 提供移动设备友好的界面
- [ ] **国际化支持** - 多语言界面支持
