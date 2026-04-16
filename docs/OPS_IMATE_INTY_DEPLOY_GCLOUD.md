# iMate 第二 Inty 后端实例：完整操作手册（gcloud 命令行）

本文与 [docs/DEVOPS_IMATE_BACKEND_PLAN.md](DEVOPS_IMATE_BACKEND_PLAN.md)、[devops/README.md](../devops/README.md)、[devops/GCP.md](../devops/GCP.md) 一致；GCP 侧步骤以 **gcloud**（及与对象存储兼容的 **gsutil**）为主。以下变量请按实际项目核对。

## 0. 约定变量（与现网文档一致）

在 shell 中导出（便于复制整段命令）：

```bash
export GCP_PROJECT="alien-paratext-461204-i9"
export GCP_REGION="asia-southeast1"
export GCP_ZONE="asia-southeast1-a"
export CLOUDSQL_INSTANCE="inty-prod"
export GCE_VM="dev-instance"

export IMATE_DB_DEV="inty-imate-dev"
export IMATE_DB_PROD="inty-imate"
export GCS_BUCKET_DEV="imate-static-dev"
export GCS_BUCKET_PROD="imate-static-prod"

export IMATE_HOST_PORT_DEV="8200"
export IMATE_HOST_PORT_PROD="8120"
export IMATE_PUBLIC_DEV="https://dev.imate.sxwl.ai/"
export IMATE_PUBLIC_PROD="https://imate.inty.cc/"
```

## 1. 本机准备

```bash
gcloud auth login
gcloud config set project "${GCP_PROJECT}"
gcloud config set compute/zone "${GCP_ZONE}"

# 建议安装组件（若尚未安装）
gcloud components install beta 2>/dev/null || true
```

验证项目与账号：

```bash
gcloud config list
gcloud projects describe "${GCP_PROJECT}" --format="value(projectId)"
```

## 2. Cloud SQL：创建 iMate 逻辑库

在**现有实例** `inty-prod` 上新增两个数据库（与 [devops/config.yaml.imate_dev](../devops/config.yaml.imate_dev)、[devops/config.yaml.imate_prod](../devops/config.yaml.imate_prod) 中 `database.db` 一致）。

```bash
gcloud sql databases create "${IMATE_DB_DEV}" \
  --instance="${CLOUDSQL_INSTANCE}" \
  --project="${GCP_PROJECT}"

gcloud sql databases create "${IMATE_DB_PROD}" \
  --instance="${CLOUDSQL_INSTANCE}" \
  --project="${GCP_PROJECT}"
```

列出库确认：

```bash
gcloud sql databases list --instance="${CLOUDSQL_INSTANCE}" --project="${GCP_PROJECT}"
```

说明：

- 连接地址、用户、密码仍与 IntelliMate 共用实例配置（私网 IP 见现网 `config.yaml.dev`）；仅 **库名** 不同。
- 若使用非 `postgres` 的独立数据库用户，需在实例上执行 `GRANT`（可用下方「直连 psql」方式）。

### 2.1 可选：用 gcloud 打开交互式 psql（授权网络场景）

若已为 Cloud SQL 开启「公网 IP + 授权网络」，可直接：

```bash
gcloud sql connect "${CLOUDSQL_INSTANCE}" \
  --user=postgres \
  --project="${GCP_PROJECT}"
```

连接后手工执行（通常 **不必**，因 `gcloud sql databases create` 已建库）：

```sql
-- 仅当需要独立角色时示例
-- CREATE ROLE imate_app LOGIN PASSWORD '...';
-- GRANT ALL PRIVILEGES ON DATABASE "inty-imate-dev" TO imate_app;
```

### 2.2 本机 Cloud SQL Auth Proxy（排障或临时连库）

取连接名并启动 Proxy（示例本地端口 `15432`）：

```bash
CONNECTION_NAME="$(gcloud sql instances describe "${CLOUDSQL_INSTANCE}" --project="${GCP_PROJECT}" --format='value(connectionName)')"
cloud-sql-proxy "${CONNECTION_NAME}" --port=15432
```

仓库内 `database` 默认 `port: 5432`。若在本机经 Proxy 跑 Alembic，需使用**仅本地使用**的 YAML 或在副本中把 `database.host` 设为 `127.0.0.1`、`database.port` 设为 `15432`，**勿将此类修改提交入库**。常规做法是直接在 **GCE VM** 上执行 Alembic（私网直连实例 IP），见第 6 节。

### 2.3 在可访问私网的环境执行 Alembic（推荐）

在 **可访问 Cloud SQL 私网** 的环境（例如已 `gcloud compute ssh` 到 `dev-instance` 且已 `git pull` 仓库）：

```bash
cd /path/to/inty   # 仓库根目录
export PYTHONPATH=.
alembic -c alembic/alembic.ini -x config=devops/config.yaml.imate_dev upgrade head
alembic -c alembic/alembic.ini -x config=devops/config.yaml.imate_prod upgrade head
```

**禁止**用 IntelliMate 的 `config.yaml.dev` / `config.yaml.prod` 对上述库执行 upgrade，以免误连错误库。

## 3. GCS：创建 iMate 专用 Bucket

使用统一对象存储命令（`gcloud storage`）：

```bash
gcloud storage buckets create "gs://${GCS_BUCKET_DEV}" \
  --project="${GCP_PROJECT}" \
  --location="${GCP_REGION}" \
  --uniform-bucket-level-access

gcloud storage buckets create "gs://${GCS_BUCKET_PROD}" \
  --project="${GCP_PROJECT}" \
  --location="${GCP_REGION}" \
  --uniform-bucket-level-access
```

列出确认：

```bash
gcloud storage buckets list --project="${GCP_PROJECT}" --filter="name:${GCS_BUCKET_DEV} OR name:${GCS_BUCKET_PROD}"
```

若团队仍使用 `gsutil`：

```bash
gsutil mb -p "${GCP_PROJECT}" -l "${GCP_REGION}" "gs://${GCS_BUCKET_DEV}"
gsutil mb -p "${GCP_PROJECT}" -l "${GCP_REGION}" "gs://${GCS_BUCKET_PROD}"
```

## 4. GCS：为后端服务账号授权

从本机密钥 JSON 读取服务账号邮箱（与容器内挂载的 `inty-backend-key.json` 一致）：

```bash
export BACKEND_SA_EMAIL="$(jq -r .client_email /path/to/inty-backend-key.json)"
echo "${BACKEND_SA_EMAIL}"
```

对两个 bucket 授予对象读写（按最小权限可改为 `roles/storage.objectUser` 等，此处与常见后端用法对齐）：

```bash
gcloud storage buckets add-iam-policy-binding "gs://${GCS_BUCKET_DEV}" \
  --member="serviceAccount:${BACKEND_SA_EMAIL}" \
  --role="roles/storage.objectAdmin" \
  --project="${GCP_PROJECT}"

gcloud storage buckets add-iam-policy-binding "gs://${GCS_BUCKET_PROD}" \
  --member="serviceAccount:${BACKEND_SA_EMAIL}" \
  --role="roles/storage.objectAdmin" \
  --project="${GCP_PROJECT}"
```

查看某 bucket 的 IAM：

```bash
gcloud storage buckets get-iam-policy "gs://${GCS_BUCKET_DEV}" --project="${GCP_PROJECT}"
```

## 5. GCE：VM、外网 IP 与 SSH

查看 `dev-instance` 外网 IP（配置 DNS A 记录时可用）：

```bash
gcloud compute instances describe "${GCE_VM}" \
  --zone="${GCP_ZONE}" \
  --project="${GCP_PROJECT}" \
  --format="get(networkInterfaces[0].accessConfigs[0].natIP)"
```

SSH 登录（需本机已配置对应密钥或 OS Login）：

```bash
gcloud compute ssh "${GCE_VM}" \
  --zone="${GCP_ZONE}" \
  --project="${GCP_PROJECT}"
```

在 VM 上创建 iMate 密钥目录并放入密钥（文件名与配置一致）：

```bash
sudo mkdir -p /opt/inty-imate-dev /opt/inty-imate-prod
sudo install -m 0600 /path/to/local/inty-backend-key.json /opt/inty-imate-dev/inty-backend-key.json
sudo install -m 0600 /path/to/local/inty-firebase-key.json /opt/inty-imate-dev/inty-firebase-key.json
sudo cp -a /opt/inty-imate-dev/inty-backend-key.json /opt/inty-imate-prod/inty-backend-key.json
sudo cp -a /opt/inty-imate-dev/inty-firebase-key.json /opt/inty-imate-prod/inty-firebase-key.json
# prod 若使用不同密钥，改为分别拷贝对应文件
sudo chown root:root /opt/inty-imate-*/*.json
```

## 6. VM 上：数据库迁移与容器（手工路径）

在 VM 上进入仓库目录（路径以你方 clone 为准，示例 `~/inty`）：

```bash
cd ~/inty && git pull
export PYTHONPATH=.
# 使用仓库内 iMate 配置，确保 database.db 已是 inty-imate-dev / inty-imate
alembic -c alembic/alembic.ini -x config=devops/config.yaml.imate_dev upgrade head
alembic -c alembic/alembic.ini -x config=devops/config.yaml.imate_prod upgrade head
```

构建并运行容器（示例；生产推荐走 GitHub Actions）：

```bash
# 在开发机或 CI 构建后 docker push；此处仅示例本地 build
sudo docker build -f devops/docker/Dockerfile \
  --build-arg CONFIG_FILE=devops/config.yaml.imate_dev \
  -t inty-server:imate-dev /path/to/repo

sudo docker stop inty-backend-imate-dev 2>/dev/null || true
sudo docker rm inty-backend-imate-dev 2>/dev/null || true
sudo docker run -d --name inty-backend-imate-dev --restart unless-stopped \
  -p "${IMATE_HOST_PORT_DEV}:8000" \
  -v /opt/inty-imate-dev/inty-backend-key.json:/inty-backend-key.json:ro \
  -v /opt/inty-imate-dev/inty-firebase-key.json:/inty-firebase-key.json:ro \
  inty-server:imate-dev
```

prod 同理：`CONFIG_FILE=devops/config.yaml.imate_prod`，端口 `8120`，目录 `/opt/inty-imate-prod/`，容器名 `inty-backend-imate-prod`。

**不要**对 `inty-backend-dev`、`inty-backend-prod` 执行 stop/rm（除非在做 IntelliMate 正式发布）。

## 7. GitHub Actions 部署（推荐）

1. 在 GitHub 仓库 Settings → Environments 新建 **`imate-dev`**、**`imate-prod`**。
2. 每个 Environment 配置 **Variables**：
   - `imate-dev`：`SERVICE_PORT_ON_HOST` = `8200`，`SERVICE_PUBLIC_URL` = `https://dev.imate.sxwl.ai/`（或团队健康检查 URL）；**Ops**：`OPS_SERVICE_PORT_ON_HOST` = `8201`，`OPS_SERVICE_PUBLIC_URL` = `https://dev.imate.inty.cc`（或 `https://dev.ops.imate.inty.cc` 备用；须与 nginx 反代域名一致，供 workflow `curl` 校验）。
   - `imate-prod`：`SERVICE_PORT_ON_HOST` = `8120`，`SERVICE_PUBLIC_URL` = `https://imate.inty.cc/`；若部署 iMate prod Ops，另配 `OPS_SERVICE_PORT_ON_HOST`、`OPS_SERVICE_PUBLIC_URL`（端口勿与 IntelliMate 冲突）。
3. Secrets 与 IntelliMate 后端部署共用（如 `DEV_SERVER_HOST`、`DEV_SERVER_USER`、`DEV_SERVER_SSH_KEY`、`LANGCHAIN_API_KEY`、`GITHUB_TOKEN` 用于 registry）。
4. 运行 workflow：[build_and_deploy_backend.yml](../.github/workflows/build_and_deploy_backend.yml) 与 [build_and_deploy_ops.yml](../.github/workflows/build_and_deploy_ops.yml)，在 **Run workflow** 中选择 Environment **`imate-dev`** 或 **`imate-prod`**。

## 8. DNS 与 TLS（域名不在 GCP 时）

若域名在 Cloudflare 等，在 DNS 控制台为 `dev.imate.sxwl.ai`、`dev.imate.inty.cc`、`dev.ops.imate.inty.cc`（iMate Ops 备用）、`imate.inty.cc` 等添加 **A** 记录，值为第 5 节查到的 VM 外网 IP。

若使用 **Cloud DNS**，示例（需已存在托管区 `ZONE_NAME`）：

```bash
export ZONE_NAME="your-dns-zone-name"
export VM_IP="$(gcloud compute instances describe "${GCE_VM}" --zone="${GCP_ZONE}" --project="${GCP_PROJECT}" --format='get(networkInterfaces[0].accessConfigs[0].natIP)')"

gcloud dns record-sets create dev.imate.sxwl.ai. \
  --zone="${ZONE_NAME}" \
  --type=A \
  --ttl=300 \
  --rrdatas="${VM_IP}" \
  --project="${GCP_PROJECT}"

gcloud dns record-sets create imate.inty.cc. \
  --zone="${ZONE_NAME}" \
  --type=A \
  --ttl=300 \
  --rrdatas="${VM_IP}" \
  --project="${GCP_PROJECT}"
```

TLS：在 VM 上按 [devops/nginx/README.md](../devops/nginx/README.md) 用 Certbot 为上述主机名签发证书后，再部署 [devops/nginx/conf.d/sxwl.ai.conf](../devops/nginx/conf.d/sxwl.ai.conf) 并执行：

```bash
sudo nginx -t && sudo systemctl reload nginx
```

或通过 [.github/workflows/deploy_nginx_conf.yaml](../.github/workflows/deploy_nginx_conf.yaml) 同步配置。

## 9. 验收检查清单

| 项 | 命令或操作 |
|----|------------|
| 库已创建 | `gcloud sql databases list --instance="${CLOUDSQL_INSTANCE}"` 含 `inty-imate-dev`、`inty-imate` |
| Bucket 已创建 | `gcloud storage ls "gs://${GCS_BUCKET_DEV}"` |
| SA 已授权 | `gcloud storage buckets get-iam-policy "gs://${GCS_BUCKET_DEV}"` 含 backend SA |
| 容器运行 | SSH 后 `sudo docker ps \| grep inty-backend-imate` |
| HTTP | `curl -sfI "${IMATE_PUBLIC_DEV}"` / prod 同理 |
| IntelliMate 未误伤 | `sudo docker ps \| grep inty-backend-dev` 与部署前一致 |

## 10. 回滚与排错

- **仅回滚 iMate**：替换 `inty-backend-imate-*` 镜像或容器，勿动 IntelliMate 容器。
- **连接 Cloud SQL 失败**：在实例详情中核对 **Authorized networks** / **Private IP** 与 VM 所在 VPC；`gcloud sql instances describe "${CLOUDSQL_INSTANCE}" --format=yaml`。
- **GCS 403**：复查第 4 节 IAM 的 `member` 是否与运行中密钥的 `client_email` 一致。

## 11. 关联文件

- 配置：[devops/config.yaml.imate_dev](../devops/config.yaml.imate_dev)、[devops/config.yaml.imate_prod](../devops/config.yaml.imate_prod)
- Nginx：[devops/nginx/conf.d/sxwl.ai.conf](../devops/nginx/conf.d/sxwl.ai.conf)
- 总览：[devops/GCP.md](../devops/GCP.md)
