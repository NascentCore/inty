# iMate 后端部署流程与安排

## 1. 文档定位

- 本文描述 iMate（IntelliMate 2.0）**独立后端实例**的部署拓扑、配置隔离、发布步骤与验收要点。
- 产品与技术边界以 [FR_IMATE_DEVELOPMENT_PLAN.md](/docs/FR_IMATE_DEVELOPMENT_PLAN.md) 为准；运维侧不重复定义业务契约。
- **代码形态**：与 IntelliMate 共用同一套 Inty 仓库与 `backend/inty` 应用（同一 Docker 构建上下文与 [devops/docker/Dockerfile](/devops/docker/Dockerfile)）。`experimental/inty_v2_text_chat_prototype` 的能力在 `app/services` 等产品路径中落地，**不**把 prototype 目录作为独立线上进程部署。

## 2. 为何单独部署

- **数据隔离**：iMate 聊天与会话数据走 `imate_*` 表；IntelliMate 继续走既有表。独立数据库实例（或同机独立库）避免误操作与备份策略混用。
- **发布节奏**：iMate 可在不触动 IntelliMate 生产容器的前提下灰度、回滚或冻结版本。
- **配置隔离**：`database_url`、GCS bucket、LangSmith project 等与 IntelliMate 分离，符合 FR 11.4、11.5。

## 3. 部署拓扑（推荐基线）

| 层级 | IntelliMate（现状） | iMate（目标） |
|------|---------------------|---------------|
| 进程 | 容器 `inty-backend-dev` / `inty-backend-prod` | 容器 `inty-backend-imate-dev` / `inty-backend-imate-prod`（名称可调整，须全局唯一） |
| 镜像 | `ghcr.io/nascentcore/inty-backend/inty-server` 同源 digest | **同一镜像**；差异来自构建时注入的 `CONFIG_FILE` |
| 配置 | `devops/config.yaml.dev` / `config.yaml.prod` | 新增 `devops/config.yaml.imate_dev`、`devops/config.yaml.imate_prod`（文件名以仓库实际为准） |
| PostgreSQL | 现有 IntelliMate 库 | **独立库**（推荐独立实例；最小可行：同 VM 第二数据库） |
| GCS | 现有 dev/prod bucket | FR 要求 dev/prod **独立 bucket**，避免对象与 URL 策略混用 |
| 入口 | 现有公网 URL + nginx → 本机端口 | **独立 host 端口**（例如与 8000 错开）+ nginx `server`/`location` 或独立子域 |
| 客户端分流 | 默认 IntelliMate | 请求头 `X-App-Id: imate_android`（FR 11.3）；**仅** iMate 官方包注入 |

Push Worker：若 iMate 首期不需要离线定时任务，可不部署 `inty-push-worker-imate-*`；需要时再按 [devops/RELEASE.md](/devops/RELEASE.md) 中 push worker 段落复制一套配置与容器名。

## 4. 配置准备（运维清单）

1. **新建配置文件**（不入库敏感值，结构与 `devops/config.yaml.dev` 对齐）：
   - `postgres_dsn` / `async_database_url` 指向 iMate 专用库。
   - `gcp` 服务账号密钥路径：与 IntelliMate 可共用密钥文件或分账号，以最小权限为准。
   - `google_play`、功能门控等与 iMate 包名/version code 对齐（若与 IntelliMate 不同包，须单独维护字段）。
2. **密钥落盘**（与现有 IntelliMate 同模式，路径示例）：
   - `/opt/inty-imate-dev/inty-backend-key.json`
   - `/opt/inty-imate-dev/inty-firebase-key.json`
   - prod 同理使用 `imate-prod` 目录。
3. **Alembic**：对 iMate 库执行与主工程一致的 migration；**禁止**对 IntelliMate 库执行含 `imate_*` 的变更来“凑合”共用。
4. **可观测性**：`LANGCHAIN_PROJECT` 或日志 label 使用独立值（例如 `inty-backend-imate-dev`），便于与 IntelliMate 日志区分。

## 5. 镜像构建与容器运行

### 5.1 本地或一次性验证

与 [backend/README.md](/backend/README.md) 一致：准备 iMate 专用 `config.yaml`，然后使用仓库根目录为 context、`CONFIG_FILE` 指向 iMate 配置构建镜像。

```bash
# 示例：构建（在仓库根目录）
docker build -f devops/docker/Dockerfile \
  --build-arg CONFIG_FILE=devops/config.yaml.imate_dev \
  -t inty-server:imate-dev .

# 示例：运行（宿主机端口按 VM 规划替换 8010）
sudo docker run --detach --log-driver=gcplogs \
  --name inty-backend-imate-dev \
  --restart unless-stopped \
  --publish 8010:8000 \
  --volume /opt/inty-imate-dev/inty-backend-key.json:/inty-backend-key.json \
  --volume /opt/inty-imate-dev/inty-firebase-key.json:/inty-firebase-key.json \
  --label application=inty-backend-imate \
  --label environment=imate-dev \
  --log-opt labels=application,environment \
  inty-server:imate-dev
```

### 5.2 与现有 GitHub Actions 对齐

当前 [build_and_deploy_backend.yml](/.github/workflows/build_and_deploy_backend.yml) 仅内置 `dev` / `prod` 两环境，容器名与 `CONFIG_FILE=devops/config.yaml.${environment}` 绑定。

**推荐演进（实施时开独立 PR）**：

1. 在 GitHub Environments 中增加 `imate-dev`、`imate-prod`（或单阶段先 `imate-dev`）。
2. 为每个 environment 配置 `vars`：`SERVICE_PORT_ON_HOST`、`SERVICE_PUBLIC_URL`（iMate 专用）。
3. 扩展 workflow：`inputs.environment` 允许选择 `imate-dev` / `imate-prod`，或在同一 job 内用矩阵/条件分支设置 `CONFIG_FILE` 与容器名前缀 `inty-backend-imate-*`。
4. 部署脚本中与 IntelliMate 相同的步骤：`docker pull` digest、`docker stop/rm`、挂载密钥、`grep Application startup complete`、对 `SERVICE_PUBLIC_URL` 做 sanity `curl`。

在 workflow 未合并前，**手动**在目标 VM 上按 5.1 拉取已构建镜像 digest 或本地 build 部署即可。

## 6. Nginx 与公网入口

- 在 [devops/nginx/conf.d/sxwl.ai.conf](/devops/nginx/conf.d/sxwl.ai.conf)（或独立 conf）中为 iMate API 增加 `proxy_pass` 到 **iMate 容器映射端口**，与 IntelliMate 的 `localhost:8000` 分离。
- TLS 证书、HSTS、WebSocket 升级头（`Upgrade`、`Connection`）与现有 IntelliMate 反代保持一致。
- 对 `/api/v1/chat/ws` 等 WS path 使用与现网相同的 proxy 超时与 buffer 策略，避免长连接被中间层提前切断。

## 7. 发布与回滚安排

| 动作 | 步骤 |
|------|------|
| 常规发布 | 合并代码 → 触发构建（同一 Dockerfile）→ 使用 iMate 专用 `CONFIG_FILE` 产出镜像 → SSH 到 VM 替换 `inty-backend-imate-*` 容器 → nginx reload（若变更）→ `curl` 健康检查 |
| 回滚 | 回退到上一已知良好 digest 的镜像，重启容器；数据库仅在有配套 down migration 时执行回滚，否则以数据修复脚本为准 |
| 冻结 | 停止自动部署 workflow 对 iMate 环境的触发，保留当前 digest 运行 |

## 8. 验收检查（DoD）

- 健康检查 URL 返回与 IntelliMate 实例一致的应用根响应（或约定的 health path）。
- 使用带 `X-App-Id: imate_android` 的客户端请求：聊天数据仅写入 `imate_*` 表；缺失或非法 `X-App-Id` 时**不得**写入 `imate_*`（见 FR 7.4）。
- IntelliMate 既有实例端口、库与 bucket 无交叉污染（抽查容器 env、config 内 DSN 与 bucket 名）。
- 结构化日志中 `application`/`environment` 标签可过滤出 iMate 实例。

## 9. 关联文档

- [FR_IMATE_DEVELOPMENT_PLAN.md](/docs/FR_IMATE_DEVELOPMENT_PLAN.md)
- [devops/README.md](/devops/README.md)
- [devops/RELEASE.md](/devops/RELEASE.md)
