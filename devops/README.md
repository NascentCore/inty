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
- **Ops 平台**：evaluation Web UI 与完整 `/api/v1`，独立镜像与工作流部署；workflow [build_and_deploy_ops.yml](../.github/workflows/build_and_deploy_ops.yml)，dev 与 prod 同 VM、不同 host 端口（8001 / 8011），nginx 将 ops.inty.cc → 8011、dev.ops.inty.cc → 8001。
- **iMate（第二 Inty 后端实例）**：与 IntelliMate **并行**，独立库、独立 GCS bucket、独立容器与域名；不得 stop/rm `inty-backend-dev` / `inty-backend-prod`。
  - 配置：[config.yaml.imate_dev](config.yaml.imate_dev)、[config.yaml.imate_prod](config.yaml.imate_prod)（构建期注入镜像，与 IntelliMate 同一 [Dockerfile](docker/Dockerfile)）。
  - 宿主机密钥目录：`/opt/inty-imate-dev/`、`/opt/inty-imate-prod/`（`inty-backend-key.json`、`inty-firebase-key.json`）。
  - 容器名：`inty-backend-imate-dev`、`inty-backend-imate-prod`；nginx 上游端口：`8020`（dev）、`8120`（prod）；公网域名：`https://dev.imate.inty.cc`、`https://imate.inty.cc`（见 [nginx/conf.d/sxwl.ai.conf](nginx/conf.d/sxwl.ai.conf)）。
  - Cloud SQL 逻辑库与 Alembic、GCS bucket 名见 [GCP.md](GCP.md)。
  - CI：[build_and_deploy_backend_imate.yml](../.github/workflows/build_and_deploy_backend_imate.yml)（需在 GitHub 创建 Environments `imate-dev` / `imate-prod`，配置 `vars.SERVICE_PORT_ON_HOST`、`vars.SERVICE_PUBLIC_URL`，与 IntelliMate 共用 `DEV_SERVER_*`、`LANGCHAIN_API_KEY` 等 secrets）。
- 操作这两个环境必须先写 python 脚本，严禁直接操作数据库、或者直接调用管理员权限的 API Endpoint，步骤如下（以 dev 为例）：
  ```bash
  ssh <gcp-vm>
  docker exec -it inty-backend-dev bash
  python scripts/<...>.py <flags>
  ```

### dev 环境测试用户

** 需要时可以随时添加**

dev 环境预制了 3 个测试用户（使用`python scripts/create_email_password_superuser.py --email test@local.ai --password test`）：
- test1@sxwl.ai sxwl666!
- test2@sxwl.ai sxwl666!
- test3@sxwl.ai sxwl666!

## 链接

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
  - `config.yaml.imate_dev` / `config.yaml.imate_prod`：iMate 第二实例配置
  - `config.yaml.local`：本地运行配置参考
  - `config.yaml.test`：CI/本地测试配置（工作流会 `cp devops/config.yaml.test config.yaml`）
- **nginx/**：反向代理配置与校验脚本
  - `nginx/nginx.conf`：Nginx 主配置
  - `nginx/conf.d/sxwl.ai.conf`：站点配置
  - `nginx/validate.sh`：配置校验
- **docker/**：运维侧的 Docker 相关材料（如有）

## Notes

同样的提示词，Cursor 搞定了，Copilot 搞不定：
* Copilot 搞不定，引入新的错误：https://github.com/NascentCore/inty/pull/2246
* Cursor 搞定，未引入新的错误：https://github.com/NascentCore/inty/pull/2249
