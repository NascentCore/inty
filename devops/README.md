# DevOps - 运维（目录索引）

**Playground:**

- https://platform.openai.com/playground/images
- https://console.cloud.google.com/vertex-ai/studio/multimodal?project=alien-paratext-461204-i9
- https://fal.ai/models/fal-ai/z-image/turbo

**LangSmith**

- dev 环境 100% 追踪
- prod 环境文本追踪采样率 1%，并仅对白名单中的运维账户强制追踪

## IntelliMate & Inty dev 与 prod 环境

- 共享同一台 gcp VM
- 差别在配置文件：[dev](config.yaml.dev) [prod](config.yaml.prod)
- **IntelliMate 数据库（dev + prod）**：均使用 **VM 上 Docker Postgres**（容器 `inty-dev-postgres`，逻辑库 `inty-dev` / `inty`），不再连 Cloud SQL；见 [LOCAL_POSTGRES.md](LOCAL_POSTGRES.md)
- **Ops 平台**：evaluation Web UI 与完整 `/api/v1`，独立镜像与工作流部署；workflow [build_and_deploy_ops.yml](../.github/workflows/build_and_deploy_ops.yml)，dev 与 prod 同 VM、不同 host 端口（8001 / 8011），nginx 将 ops.inty.cc → 8011、dev.ops.inty.cc → 8001。手动选择 GitHub Environment `imate-dev` / `imate-prod` / **`imate`** 可部署 iMate 相关 Ops（容器 `inty-ops-imate-*` 或 `inty-ops-imate`，与 IntelliMate 的 `inty-ops-dev` 等并行）。
- **iMate（第二 Inty 后端实例）**：与 IntelliMate **并行**，独立库、独立 GCS bucket、独立容器与域名；不得 stop/rm `inty-backend-dev` / `inty-backend-prod`。
  - 配置：[config.yaml.imate_dev](config.yaml.imate_dev)、[config.yaml.imate_prod](config.yaml.imate_prod)、[config.yaml.imate](config.yaml.imate)（构建期注入镜像，与 IntelliMate 同一 [Dockerfile](docker/Dockerfile)）。
  - 宿主机密钥目录：`/opt/inty-imate-dev/`、`/opt/inty-imate-prod/`、**`/opt/inty-imate/`**（`inty-backend-key.json`、`inty-firebase-key.json`）。
  - 容器名：`inty-backend-imate-dev`、`inty-backend-imate-prod`；推荐宿主机端口：**8200**（dev 后端）、**8201**（dev Ops）；GitHub `imate-dev` 公网：`SERVICE_PUBLIC_URL` = `https://dev.imate.sxwl.ai/`，`OPS_SERVICE_PUBLIC_URL` = **`https://dev.imate.inty.cc`**（亦可保留 `https://dev.ops.imate.inty.cc` 作备用）；nginx：`dev.imate.sxwl.ai` → **8200**（后端），`dev.imate.inty.cc` 与 `dev.ops.imate.inty.cc` → **8201**（Ops，后者证书为 `dev.ops.inty.cc`）。GitHub Environment **`imate`**（Ops 专用逻辑库 `imate`）：`OPS_SERVICE_PUBLIC_URL` 典型为 `https://imate.inty.cc`，`OPS_SERVICE_PORT_ON_HOST` 典型 **8301**，nginx 将 **`imate.inty.cc` → 8301**（见 [nginx/conf.d/sxwl.ai.conf](nginx/conf.d/sxwl.ai.conf)）；**不再**在同一域名上反代原 iMate prod 后端 :8120，若后端仍需公网请另设子域。证书由 VM 上 certbot 签发，路径与 `ssl_certificate` 一致。
  - Cloud SQL 逻辑库与 Alembic、GCS bucket 名见 [GCP.md](GCP.md)；独立 Ops 库 **`imate`** 操作见 [docs/OPS_IMATE_ENV_IMATE_RUNBOOK.md](../docs/OPS_IMATE_ENV_IMATE_RUNBOOK.md)。
  - CI：与 IntelliMate 共用 [build_and_deploy_backend.yml](../.github/workflows/build_and_deploy_backend.yml)、[build_and_deploy_ops.yml](../.github/workflows/build_and_deploy_ops.yml)，在 **Run workflow** 中选择 Environment **`imate-dev`**、**`imate-prod`** 或 **`imate`**（勿用 `dev`/`prod` 部署 iMate 专用实例）。GitHub Environment `imate-dev` / `imate-prod` 需配置 `vars.SERVICE_PORT_ON_HOST`、`vars.SERVICE_PUBLIC_URL`（如 `https://dev.imate.sxwl.ai/`）；**另**为 iMate Ops 配置 `vars.OPS_SERVICE_PORT_ON_HOST`（dev 建议 **8201**）、`vars.OPS_SERVICE_PUBLIC_URL`（如 **`https://dev.imate.inty.cc`** 或 `https://dev.ops.imate.inty.cc` 供 workflow curl）。Environment **`imate`** 需 `vars.OPS_SERVICE_PORT_ON_HOST`、`vars.OPS_SERVICE_PUBLIC_URL`。与 IntelliMate 共用 `DEV_SERVER_*`、`LANGCHAIN_API_KEY` 等 secrets。`devops/config.yaml.imate*` 未列入 Ops workflow 的 `on.push.paths`，避免仅改 iMate 配置却自动重部署 IntelliMate Ops；部署 iMate Ops 请用手动 workflow。
- 操作这两个环境必须先写 python 脚本，严禁直接操作数据库、或者直接调用管理员权限的 API Endpoint，步骤如下（以 dev 为例）：
  ```bash
  ssh <gcp-vm>
  docker exec -it inty-backend-dev bash
  python tools/scripts/<...>.py <flags>
  ```

### dev 环境测试用户

** 需要时可以随时添加**

dev 环境预制了 3 个测试用户（使用`python tools/scripts/create_email_password_superuser.py --email test@local.ai --password test`）：
- test1@sxwl.ai sxwl666!
- test2@sxwl.ai sxwl666!
- test3@sxwl.ai sxwl666!

## 链接

- [IntelliMate 本地 Postgres（Docker，dev + prod）](LOCAL_POSTGRES.md)
- [prod push worker logs](https://cloudlogging.app.goo.gl/VXHGrai93hqJU3er9)
- [dev push worker logs](https://cloudlogging.app.goo.gl/xhWv88U4bH7v7UNd9)
- [prod inty backend logs](https://cloudlogging.app.goo.gl/9fr7rxgrwbas68En9)
- [dev inty backend logs](https://cloudlogging.app.goo.gl/aaPiWvxr7syuAFuX7)
- [LangSmith IntelliMate-dev project](https://smith.langchain.com/o/1463b2d0-5d84-4f0c-b31e-0a158d823e01)
- [LangSmith inty-backend-prod tracing project](https://smith.langchain.com/o/824a4bb5-ca84-4fa2-969e-7a50cd267999/projects/p/2808d56c-e07f-4293-8bec-1cc62d9f4975)
- [Sentry plan overview](https://inty-inc.sentry.io/settings/billing/overview/): 生产环境追踪等 Observability 需求

## 非 .md 文件与子目录概述

- **配置文件**：
  - `config.yaml.dev` / `config.yaml.prod`：IntelliMate 部署环境配置（构建期注入进入镜像；具体机制见 `RELEASE.md`）
    - **dev / prod**：`database` 均指向 VM 本地 Docker Postgres（[LOCAL_POSTGRES.md](LOCAL_POSTGRES.md)）
  - `config.yaml.imate_dev` / `config.yaml.imate_prod`：iMate 第二实例配置
  - `config.yaml.local`：工程师本机 Ops / REPL 配置；通过 **`export INTY_CONFIG_YAML=devops/config.yaml.local`** 加载（Postgres **`localhost:15432`**，db **`inty`**）
  - `config.yaml.test`：CI / 本地 pytest 配置（**`INTY_CONFIG_YAML=devops/config.yaml.test`**）；**`database` 段与 `config.yaml.local` 相同 DSN**，可连 Ops 已 migrate 的同一 Postgres；差异仅在 agent / tracing / 外部服务 mock
- **nginx/**：反向代理配置与校验脚本
  - `nginx/nginx.conf`：Nginx 主配置
  - `nginx/conf.d/sxwl.ai.conf`：站点配置
  - `nginx/validate.sh`：配置校验
- **docker/**：运维侧的 Docker 相关材料（如有）
