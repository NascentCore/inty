# Docker 构建文件
<!-- CREATED_BY_AGENT -->

本目录包含用于构建 Inty 后端服务的 Dockerfile。

## Dockerfile 说明

### `Dockerfile`

用于构建 Inty 后端主服务的 Docker 镜像。该镜像包含：

- **后端构建阶段**：基于 Python 3.12，包含所有后端依赖和系统工具
- **运行时阶段**：包含完整的应用代码、数据库迁移工具和启动脚本

**构建要求**：
- 平台：AMD64 (x86_64) - 由于 animeface 依赖限制
- 必需构建参数：`CONFIG_FILE` - 配置文件路径
- 可选构建参数（推荐 CI 传入，便于运行中 `GET /` 与日志暴露 VCS 修订）：
  - `INTY_VCS_REVISION`：git commit SHA（或 `GITHUB_SHA` 在运行时也可被应用读取）
  - `INTY_BUILD_TIME`：UTC ISO8601，例如 `2026-04-06T12:00:00Z`
  - `INTY_VCS_DIRTY`：`true` / `false`（本地脏构建时）

**构建示例**：

```bash
# 从项目根目录构建
docker build \
  --build-arg CONFIG_FILE=devops/config.yaml.prod \
  --build-arg INTY_VCS_REVISION=$(git rev-parse HEAD) \
  --build-arg INTY_BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
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
- 可选：`INTY_VCS_REVISION`、`INTY_BUILD_TIME`、`INTY_VCS_DIRTY`（与主服务 `Dockerfile` 相同，见上文）

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

### `Dockerfile.ops`

用于构建 Ops 平台（evaluation Web UI + 完整 `/api/v1`）的 Docker 镜像，与后端主服务分离部署。镜像包含 evaluation 前端构建结果与 ops 启动脚本，监听端口 8001。

**构建要求**：

- 平台：AMD64 (x86_64)
- 必需构建参数：`CONFIG_FILE` - 配置文件路径
- 可选：`INTY_VCS_REVISION`、`INTY_BUILD_TIME`、`INTY_VCS_DIRTY`（与主服务 `Dockerfile` 相同）

**构建示例**：

```bash
# 从项目根目录构建
docker build \
  --build-arg CONFIG_FILE=devops/config.yaml.prod \
  -f devops/docker/Dockerfile.ops \
  -t inty-ops:latest \
  .
```

**运行示例**：

```bash
docker run -d \
  --name inty-ops \
  -p 8001:8001 \
  -v /path/to/inty-backend-key.json:/inty-backend-key.json:ro \
  -v /path/to/inty-firebase-key.json:/inty-firebase-key.json:ro \
  inty-ops:latest
```

部署流程见 `.github/workflows/build_and_deploy_ops.yml`；dev/prod 同 VM，分别使用 host 端口 8001、8101，nginx 将 ops.inty.cc 反代到 8101、dev.ops.inty.cc 反代到 8001。

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

上述 Dockerfile 均安装以下系统依赖：

- `build-essential` - C/C++ 编译工具链
- `libpq-dev` - PostgreSQL 客户端库
- `ffmpeg` - 音视频处理工具

## 多阶段构建

Ops 的 Dockerfile 采用前后端多阶段构建：

1. **frontend-builder**：构建前端静态文件
2. **base**：安装 Python 依赖和系统工具
3. **最终阶段**：组装完整的运行时镜像

主服务与 push-worker 的 Dockerfile 仅保留 Python 后端构建阶段，不再构建 evaluation 前端静态资源。

## 注意事项

1. **平台限制**：由于 animeface 依赖，仅支持 AMD64 架构
2. **配置文件必需**：构建时必须提供 `CONFIG_FILE` 参数，否则构建会失败
3. **缓存优化**：使用 BuildKit 缓存机制加速 pip 依赖安装
4. **前端构建**：仅 Ops Dockerfile 构建 evaluation 前端；主服务与 push-worker 镜像不包含该阶段

## 相关文档

- 部署流程：参见 `devops/README.md`
- 推送服务详情：参见 `devops/README.md#推送服务部署`
- 启动脚本：`backend/inty/start.sh`（后端主服务）、`backend/push_worker/start.sh`（推送服务）、`backend/ops/start.sh`（Ops 平台）
