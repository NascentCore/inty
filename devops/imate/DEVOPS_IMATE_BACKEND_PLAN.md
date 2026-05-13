# iMate 后端部署流程与安排

## 1. 文档定位

- 本文描述 iMate（IntelliMate 2.0）**独立后端实例**的部署拓扑、配置隔离、发布步骤与验收要点。
- 产品与技术边界以 [FR_IMATE_DEVELOPMENT_PLAN.md](/docs/FR_IMATE_DEVELOPMENT_PLAN.md) 为准；运维侧不重复定义业务契约。
- **代码形态**：与 IntelliMate 共用同一套 Inty 仓库与 `backend/inty` 应用（同一 Docker 构建上下文与 [devops/docker/Dockerfile](/devops/docker/Dockerfile)）。`experimental/inty_v2_text_chat_prototype` 的能力在 `app/services` 等产品路径中落地，**不**把 prototype 目录作为独立线上进程部署。

## 2. IntelliMate 既有实例不变（强制）

以下约束优先级高于本文其余「推荐」表述；任何 iMate 部署方案**不得**违背。

- **保留对象**：为 **IntelliMate Android App** 服务的现有后端实例维持现状，包括但不限于：
  - 容器名：`inty-backend-dev`、`inty-backend-prod`（及与之配套的 push worker 容器名，若存在）。
  - 宿主机端口、nginx `server_name`、TLS 证书、公网入口 URL（与现网 IntelliMate 客户端配置的 base URL 一致）。
  - 所用 `devops/config.yaml.dev` / `config.yaml.prod`、PostgreSQL 库、GCS bucket、密钥挂载路径（`/opt/inty-dev/`、`/opt/inty-prod/` 等现有约定）。
- **禁止操作**：在 iMate 发布、回滚、调试、workflow 实验过程中，**不得**对上述 IntelliMate 容器执行 `docker stop` / `docker rm` / 替换镜像 / 改绑端口 / 改写指向 IntelliMate 的 nginx 上游，除非走**独立的 IntelliMate 发布流程**（例如 [build_and_deploy_backend.yml](/.github/workflows/build_and_deploy_backend.yml) 在明确选择 `dev`/`prod` 且仅操作 `inty-backend-dev`/`prod` 时）。
- **新增而非替换**：iMate 仅通过**额外**容器（如 `inty-backend-imate-dev`）、**额外**端口、**额外**域名（如 `imate.inty.cc`）、**额外**配置文件与 GitHub Environment 变量接入；与 IntelliMate 并存在同一 VM 时，属于**旁路扩容**，不是升级或切换唯一实例。
- **工作流隔离**：iMate 与 IntelliMate 共用 [build_and_deploy_backend.yml](/.github/workflows/build_and_deploy_backend.yml)，通过 GitHub Environment 区分；部署脚本**不得**再使用单一的 `inty-backend-${{ env }}` 命名，须使用 workflow 内 **`map`** 输出的容器名与密钥目录（`inty-backend-imate-*` 与 `/opt/inty-imate-*`），避免误伤 `inty-backend-dev` / `inty-backend-prod`。
- **验收门禁**：每次 iMate 部署完成后，在变更单或流水线 summary 中勾选：IntelliMate 容器仍在运行、`docker inspect` 镜像 digest 与部署前一致（除非同日另有 IntelliMate 发布）。

## 3. 为何单独部署

- **数据隔离**：iMate 聊天与会话数据走 `imate_*` 表；IntelliMate 继续走既有表。独立数据库实例（或同机独立库）避免误操作与备份策略混用。
- **发布节奏**：iMate 可在不触动 IntelliMate 生产容器的前提下灰度、回滚或冻结版本。
- **配置隔离**：`database_url`、GCS bucket、LangSmith project 等与 IntelliMate 分离，符合 FR 11.4、11.5。

## 4. 部署拓扑（推荐基线）

| 层级 | IntelliMate（现状，禁止被 iMate 流程改动） | iMate（目标，仅 additive） |
|------|------------------------------------------|----------------------------|
| 进程 | 容器 `inty-backend-dev` / `inty-backend-prod` | 容器 `inty-backend-imate-dev` / `inty-backend-imate-prod`（名称可调整，须全局唯一且**不得**与上列重名） |
| 镜像 | `ghcr.io/nascentcore/inty-backend/inty-server` 同源 digest | **同一镜像构建线**；差异来自构建时注入的 `CONFIG_FILE` |
| 配置 | `devops/config.yaml.dev` / `config.yaml.prod` | 新增 `devops/config.yaml.imate_dev`、`devops/config.yaml.imate_prod`（文件名以仓库实际为准） |
| PostgreSQL | 现有 IntelliMate 库 | **独立库**（推荐独立实例；最小可行：同 VM 第二数据库） |
| GCS | 现有 dev/prod bucket | FR 要求 dev/prod **独立 bucket**，避免对象与 URL 策略混用 |
| 入口 | 现有公网 URL + nginx → IntelliMate 容器端口 | **独立 host 端口**（与 IntelliMate 映射端口不同）+ nginx 独立 `server` / `server_name`（如 `imate.inty.cc`） |
| 客户端分流 | IntelliMate App 仅连接既有域名 | iMate App 仅连接 iMate 域名；请求头 `X-App-Id: imate_android` 等策略按 FR 11.3 在 iMate 链路上执行 |

Push Worker：若 iMate 首期不需要离线定时任务，可不部署 `inty-push-worker-imate-*`；需要时再按 [devops/RELEASE.md](/devops/RELEASE.md) 中 push worker 段落复制一套配置与容器名，且**不得**替换 `inty-push-worker-dev` / `inty-push-worker-prod`。

## 5. 配置准备（运维清单）

1. **新建配置文件**（不入库敏感值，结构与 `devops/config.yaml.dev` 对齐）：
   - `postgres_dsn` / `async_database_url` 指向 iMate 专用库。
   - `gcp` 服务账号密钥路径：与 IntelliMate 可共用密钥文件或分账号，以最小权限为准。
   - `google_play`、功能门控等与 iMate 包名/version code 对齐（若与 IntelliMate 不同包，须单独维护字段）。
2. **密钥落盘**（**独立目录**，避免覆盖 `/opt/inty-dev`、`/opt/inty-prod` 下 IntelliMate 文件）：
   - `/opt/inty-imate-dev/inty-backend-key.json`
   - `/opt/inty-imate-dev/inty-firebase-key.json`
   - prod 同理使用 `imate-prod` 目录。
3. **Alembic**：对 iMate 库执行 migration 时**必须**使用 iMate 专用配置文件中的数据库 URL（见下节）；**禁止**在未显式指定 iMate 配置时执行命令，以免误连 IntelliMate 库。版本文件仍来自仓库 `backend/alembic/versions/`（与 IntelliMate 共用同一套 revision 链），变更通过同一仓库 PR 管理。
4. **可观测性**：`LANGCHAIN_PROJECT` 或日志 label 使用独立值（例如 `inty-backend-imate-dev`），便于与 IntelliMate 日志区分。

## 6. Alembic 与 `backend/alembic/versions`（绑定 iMate `config.yaml`）

- **事实来源**：`backend/alembic/env.py` 通过 `runtime_config.database.url` 连接数据库；若使用 `-x config=<path>`，则从该路径加载配置（见 [backend/alembic/env.py](/backend/alembic/env.py) 中 `_load_runtime_config`）。因此**指向哪套库完全由所选配置文件决定**，与 `backend/alembic/versions` 目录下的 revision 文件无独立「iMate 专用版本目录」；**同一代码库、同一 `versions/` 树**分别对 IntelliMate 库与 iMate 库执行 `upgrade` 时，各自写入对应库中的 `alembic_version` 表。
- **iMate 库操作（推荐命令形态）**：在仓库根目录执行，**显式**传入 iMate 的 `devops/config.yaml.imate_dev`（或 prod 等价文件），**不得**依赖默认 `config.yaml`（避免与本地或 IntelliMate 配置混淆）：

```bash
export PYTHONPATH=.
export ALEMBIC_CONFIG=backend/alembic/alembic.ini
alembic -c backend/alembic/alembic.ini -x config=devops/config.yaml.imate_dev upgrade head
```

- **生成新 revision**：若需 `revision --autogenerate`，同样**必须**加 `-x config=...` 指向 iMate 配置，且仅在已确认 URL 指向 iMate 库后执行；生成出的文件仍落在 `backend/alembic/versions/`，合并后 IntelliMate 与 iMate 部署在各自发布流程中对**各自**库执行 `upgrade head`（先 dev 验证，再 prod）。详见 [backend/alembic/AGENTS.md](/backend/alembic/AGENTS.md)。
- **隔离门禁**：对 IntelliMate 库执行 Alembic 时使用 IntelliMate 的 `config.yaml.dev` / `config.yaml.prod`（或团队约定路径）；**禁止**用 IntelliMate 配置对 iMate 库升级或反向操作，除非刻意做同一库（与本计划矛盾）。

## 7. 镜像构建与容器运行

### 7.1 本地或一次性验证

与 [backend/README.md](/backend/README.md) 一致：准备 iMate 专用 `config.yaml`，然后使用仓库根目录为 context、`CONFIG_FILE` 指向 iMate 配置构建镜像。

```bash
# 示例：构建（在仓库根目录）
docker build -f devops/docker/Dockerfile \
  --build-arg CONFIG_FILE=devops/config.yaml.imate_dev \
  -t inty-server:imate-dev .

# 示例：运行（宿主机端口按 VM 规划替换 8010，且必须与 IntelliMate 已占用端口不冲突）
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

### 7.2 与现有 GitHub Actions 对齐

[iMate 后端与 IntelliMate 共用](/.github/workflows/build_and_deploy_backend.yml)同一 workflow：在 **Run workflow** 中选择 GitHub Environment `dev` / `prod`（IntelliMate）或 `imate-dev` / `imate-prod`（iMate）。workflow 内 **`map`** 步骤将环境名映射到 `CONFIG_FILE`、容器名（`inty-backend-imate-*` vs `inty-backend-dev`/`prod`）、密钥目录与 Docker `application` label；**schedule** 仍仅部署 IntelliMate **`prod`**，不会自动部署 iMate。

[iMate Ops](/.github/workflows/build_and_deploy_ops.yml) 与 IntelliMate Ops 共用同一 workflow；选择 `imate-dev` / `imate-prod` 时使用 `devops/config.yaml.imate_*`，容器 `inty-ops-imate-*`（与 `inty-ops-dev` 等并行）。`imate` 专用配置文件**未**列入 Ops 的 `on.push.paths`，避免误触发 IntelliMate Ops 重部署；iMate Ops 以 **手动** workflow 为主。

1. 在 GitHub Environments 中配置 `imate-dev`、`imate-prod` 的 `vars`：`SERVICE_PORT_ON_HOST`、`SERVICE_PUBLIC_URL`；部署 Ops 时另加 `OPS_SERVICE_PORT_ON_HOST`、`OPS_SERVICE_PUBLIC_URL`。
2. **禁止**在误选 `dev`/`prod` 时期望部署 iMate；也禁止在脚本中混用环境名导致对 `inty-backend-dev` / `inty-backend-prod` 的 stop/rm（iMate 路径仅操作 `inty-backend-imate-*`，由 `map` 输出保证）。

若 CI 不可用，**手动**在目标 VM 上按 7.1 拉取已构建镜像 digest 或本地 build 部署即可。

## 8. Nginx 与公网入口

- **新增** `server`（或独立 conf 文件）将 **iMate 域名** `proxy_pass` 到 **iMate 容器映射端口**；**不要**修改现有 IntelliMate `server` 块中指向 IntelliMate 后端的 `proxy_pass` 目标，除非正在进行 IntelliMate 自己的变更。
- TLS 证书、HSTS、WebSocket 升级头（`Upgrade`、`Connection`）与现有 IntelliMate 反代保持一致。
- 对 `/api/v1/chat/ws` 等 WS path 使用与现网相同的 proxy 超时与 buffer 策略，避免长连接被中间层提前切断。

## 9. 发布与回滚安排

| 动作 | 步骤 |
|------|------|
| 常规发布 | 合并代码 → **对 iMate 库**执行 `alembic upgrade head -x config=devops/config.yaml.imate_*`（在部署容器前或按团队约定顺序）→ 构建镜像（同一 Dockerfile + iMate `CONFIG_FILE`）→ **仅**替换 `inty-backend-imate-*` 容器 → 仅当 iMate 域名/nginx 有变更时 reload 对应 `server` → 对 iMate 公网 URL `curl` 健康检查。**禁止**在本流程中重启或替换 IntelliMate 容器。 |
| 回滚 | 回退 iMate 实例到上一已知良好 digest；IntelliMate 实例不参与回滚。 |
| 冻结 | 暂停对 GitHub Environment `imate-*` 的手动部署；IntelliMate 的 `dev`/`prod` 定时与手动发布保持独立。 |

## 10. 验收检查（DoD）

- iMate：健康检查 URL 可用；`alembic_version` 与已部署代码 revision 一致且该次 migration 使用的 `-x config` 为 iMate 专用文件；带 `X-App-Id: imate_android`（若采用）时聊天数据仅写入 `imate_*` 表；缺失或非法 `X-App-Id` 时**不得**写入 `imate_*`（见 FR 7.4）。
- **IntelliMate 不受影响（强制）**：部署 iMate 前后，IntelliMate 容器仍在运行且名称未变；`config` 内 DSN/bucket 仍指向 IntelliMate 资源；IntelliMate 公网入口行为与部署前一致（可用 spot check：`curl` 或版本检查接口）。
- 结构化日志中 `application`/`environment` 标签可过滤出 iMate 实例，且不与 IntelliMate 日志混为一谈。

## 11. 关联文档

- [FR_IMATE_DEVELOPMENT_PLAN.md](/docs/FR_IMATE_DEVELOPMENT_PLAN.md)
- [devops/README.md](/devops/README.md)
- [devops/RELEASE.md](/devops/RELEASE.md)
- [backend/alembic/AGENTS.md](/backend/alembic/AGENTS.md)
