# Docker 构建文件
<!-- CREATED_BY_AGENT -->

本目录包含用于构建 Inty 后端服务的 Dockerfile。

## Dockerfile 说明

### `Dockerfile`

用于构建 Inty 后端主服务的 Docker 镜像。该镜像包含：

- **前端构建阶段**：使用 Node.js 构建 `evaluation/` 前端应用
- **后端构建阶段**：基于 Python 3.12，包含所有后端依赖和系统工具
- **运行时阶段**：包含完整的应用代码、数据库迁移工具和启动脚本

**构建要求**：
- 平台：AMD64 (x86_64) - 由于 animeface 依赖限制
- 必需构建参数：`CONFIG_FILE` - 配置文件路径

**构建示例**：

```bash
# 从项目根目录构建
docker build \
  --build-arg CONFIG_FILE=devops/config.yaml.prod \
  -f devops/docker/Dockerfile \
  -t inty-backend:latest \
  .
```

**运行示例**：

```bash
docker run -d \
  --name inty-backend \
  -p 8000:8000 \
  -v /path/to/key.json:/opt/inty/inty-backend-key.json:ro \
  -v /path/to/firebase-key.json:/opt/inty/inty-firebase-key.json:ro \
  inty-backend:latest
```

### `Dockerfile.push-worker`

用于构建推送服务（Push Worker）的 Docker 镜像。推送服务独立于后端主服务运行，负责处理推送通知任务。

**构建要求**：
- 平台：AMD64 (x86_64) - 由于 animeface 依赖限制
- 必需构建参数：`CONFIG_FILE` - 配置文件路径

**构建示例**：

```bash
# 从项目根目录构建
docker build \
  --build-arg CONFIG_FILE=devops/config.yaml.prod \
  -f devops/docker/Dockerfile.push-worker \
  -t inty-push-worker:latest \
  .
```

**运行示例**：

```bash
docker run -d \
  --name inty-push-worker \
  -v /path/to/key.json:/opt/inty/inty-backend-key.json:ro \
  -v /path/to/firebase-key.json:/opt/inty/inty-firebase-key.json:ro \
  inty-push-worker:latest
```

## 构建上下文

**重要**：所有 Dockerfile 的构建上下文应为**项目根目录**，而不是 `devops/docker/` 目录。构建时使用 `-f` 参数指定 Dockerfile 路径。

```bash
# 正确：从项目根目录构建
cd /path/to/inty
docker build -f devops/docker/Dockerfile -t inty-backend .

# 错误：从 devops/docker/ 目录构建
cd /path/to/inty/devops/docker
docker build -f Dockerfile -t inty-backend .
```

## 配置文件

构建时需要提供配置文件路径作为 `CONFIG_FILE` 构建参数。配置文件应位于 `devops/` 目录下：

- `devops/config.yaml.dev` - 开发环境配置
- `devops/config.yaml.prod` - 生产环境配置
- `devops/config.yaml.test` - 测试环境配置
- `devops/config.yaml.local` - 本地开发配置

## 系统依赖

两个 Dockerfile 都安装以下系统依赖：

- `build-essential` - C/C++ 编译工具链
- `libpq-dev` - PostgreSQL 客户端库
- `ffmpeg` - 音视频处理工具

## 多阶段构建

两个 Dockerfile 都采用多阶段构建：

1. **frontend-builder**：构建前端静态文件
2. **base**：安装 Python 依赖和系统工具
3. **最终阶段**：组装完整的运行时镜像

## 注意事项

1. **平台限制**：由于 animeface 依赖，仅支持 AMD64 架构
2. **配置文件必需**：构建时必须提供 `CONFIG_FILE` 参数，否则构建会失败
3. **缓存优化**：使用 BuildKit 缓存机制加速 pip 依赖安装
4. **前端构建**：推送服务 Dockerfile 虽然包含前端构建阶段，但实际运行时不需要前端资源（保留以保持一致性）

## 相关文档

- 部署流程：参见 `devops/README.md`
- 推送服务详情：参见 `devops/README.md#推送服务部署`
- 启动脚本：`backend/inty/start.sh`（后端主服务）、`backend/push_worker/start.sh`（推送服务）
