# GitHub Environment `imate`（Ops）操作手册

与 [devops/README.md](../devops/README.md)、[devops/GCP.md](../devops/GCP.md)、[OPS_IMATE_INTY_DEPLOY_GCLOUD.md](OPS_IMATE_INTY_DEPLOY_GCLOUD.md) 一致。

## 约定

| 项 | 值 |
|----|-----|
| GCP 项目 | `alien-paratext-461204-i9` |
| Cloud SQL 实例 | `inty-prod` |
| 逻辑库名 | `imate` |
| 构建配置 | [devops/config.yaml.imate](../devops/config.yaml.imate) |
| GitHub Environment | `imate` |
| 建议 `vars` | `OPS_SERVICE_PORT_ON_HOST=8301`，`OPS_SERVICE_PUBLIC_URL=https://imate.inty.cc` |
| 容器名 | `inty-ops-imate` |
| VM 密钥目录 | `/opt/inty-imate/`（`inty-backend-key.json`、`inty-firebase-key.json`） |

## 1. 创建 Cloud SQL 逻辑库 `imate`

```bash
export GCP_PROJECT="alien-paratext-461204-i9"
export CLOUDSQL_INSTANCE="inty-prod"

gcloud config set project "${GCP_PROJECT}"

gcloud sql databases create imate \
  --instance="${CLOUDSQL_INSTANCE}" \
  --project="${GCP_PROJECT}"

gcloud sql databases list --instance="${CLOUDSQL_INSTANCE}" --project="${GCP_PROJECT}"
```

若库已存在，跳过后续「创建」即可。

## 2. Alembic 迁移（指向 `imate` 库）

在可访问数据库私网 IP 的环境执行（勿用 `config.yaml.dev` / `prod` 误连 IntelliMate）：

```bash
export PYTHONPATH=.
alembic -c alembic/alembic.ini -x config=devops/config.yaml.imate upgrade head
```

## 3. VM：密钥目录

在 `ssh inty` 上确保目录与文件存在（可与其它 iMate 目录权限对齐）：

```bash
sudo mkdir -p /opt/inty-imate
# 将 inty-backend-key.json、inty-firebase-key.json 放入该目录（与 workflow volume 一致）
sudo chmod 700 /opt/inty-imate
```

## 4. TLS 与 Nginx

- 仓库配置：[devops/nginx/conf.d/sxwl.ai.conf](../devops/nginx/conf.d/sxwl.ai.conf) 中 `imate.inty.cc` 反代至 **8301**（与 GitHub `vars` 一致）。
- VM 上若尚无证书：`certbot` 为 `imate.inty.cc` 签发后，路径应与 `ssl_certificate` 中 `/etc/letsencrypt/live/imate.inty.cc/` 一致；`nginx -t` 后 `reload`。

## 5. GitHub Actions

合并包含 workflow 与配置的变更后，打开 **Release - Inty Ops 平台**，**Run workflow**，Environment 选 **`imate`**。

依赖与其它 Ops 部署相同：`DEV_SERVER_*`、`LANGCHAIN_API_KEY` 等；本环境额外依赖 **`imate` Environment** 下的 `OPS_SERVICE_PORT_ON_HOST`、`OPS_SERVICE_PUBLIC_URL`。

## 6. 验证

```bash
curl -v --fail --retry 3 --retry-delay 3 "https://imate.inty.cc/"
```

## 回滚

- Nginx：将 `imate.inty.cc` 的 `proxy_pass` 改回所需上游端口并 `reload`。
- 容器：`sudo docker stop inty-ops-imate && sudo docker rm inty-ops-imate`（按需）。

## 说明

`imate.inty.cc` 若曾指向 iMate **后端**（例如 :8120），改为 Ops（:8301）后，原后端公网入口需另域名或端口；部署前请与产品约定。
