# Inty-eval（角色评测工具）

这是一个使用 React/TypeScript 构建的运行于浏览器内的 Web 应用程序，用于评估 AI 角色、管理提示和显示聊天交互。

```
git clone https://github.com/NascentCore/inty.git
cd inty

# 默认对接 https://dev.inty.sxwl.ai/api/v1
# 打开 http://localhost:3000/
evaluation/start.sh

# 如果需要对接本地运行的后端服务
# 会在数据库内初始化超级用户
docker compose up --build

# 指向本地服务
# 打开 http://localhost:3000/
evaluation/start.sh --backend-url http://localhost:8000/api/v1
```

## langsmith 上查看大模型调用请求

点击单角色聊天的 langsmith 标志；如请求没有显示，则需要刷新页面
<img width="800" height="1026" alt="image" src="https://github.com/user-attachments/assets/ab88bf82-fb3b-4cab-b169-bf7b0f17bdeb" />

## 使用本地 Inty 后端地址

在本代码库顶层目录，运行 `docker compose up --build` 来启动本地后端，
启动后，后端地址位于 `http://localhost:8000/api/v1`，该地址要填入 Inty-eval 所使用的后端地址。

然后，需要向 Inty 后端数据库内写入预置的用户信息，以便让 inty-eval 可以通过内置的用户名来访问本地 inty 后端。
登录后端数据库：`docker exec -it inty-backend-pgvector-1 psql -U postgres -d inty`
然后运行以下 SQL 指令

```psql
INSERT INTO users (
    id,
    nickname,
    email,
    gender,
    age_group,
    description,
    is_active,
    is_superuser,
    auth_type,
    readable_id
) VALUES (
    'user-01JWZ34Y4D1C92GD86A5R6EWYJ',
    'admin',
    'admin@sxwl.ai',
    'MALE',
    '18-24',
    'An admin user',
    true,
    true,
    'GOOGLE',
    '11111111'
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

## ⚙️ 配置选项

### 环境变量配置

1. **构建时环境变量**

```bash
# Dockerfile中的ARG参数
ARG REACT_APP_API_BASE_URL=https://dev.inty.sxwl.ai/api/v1
ARG REACT_APP_ENV=production
```

1. **开发环境变量**

```bash
# .env文件
REACT_APP_API_BASE_URL=https://dev.inty.sxwl.ai/api/v1
REACT_APP_ENV=development
```

### Vite配置 (vite.config.ts)

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
