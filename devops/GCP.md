# GCP

## BigQuery CloudSQL-Postgres 链接

https://docs.cloud.google.com/bigquery/docs/working-with-connections#console_1
BigQuery Federated Queries (for on-demand querying)

DataStream 比较麻烦，因为需要从主数据库同步数据、要重启数据库；

- [ ] 是否能在只读副本上直接增加数据同步到 big query？ <img width="600" height="608" alt="image" src="https://github.com/user-attachments/assets/cdb6bce5-beb9-4d56-ad08-c3e53eae8c48" /> <img width="600" height="750" alt="image" src="https://github.com/user-attachments/assets/6e50aaa5-d5ef-449c-8bd0-b545cebcd667" />


## Dev/Prod 环境概览（Inty）

本节记录线上/开发环境的基础信息与常用入口（与发布流程相关的操作请见 `RELEASE.md`）。

- **GCP zone**：asia-southeast1-a
- **数据库**：共用同一 CloudSQL Postgres 实例，dev:inty-dev prod:inty
  - [看板](https://console.cloud.google.com/sql/instances/inty-prod/system-insights?project=alien-paratext-461204-i9)
  - [查询性能分析](https://console.cloud.google.com/sql/instances/inty-prod/insights;duration=P1D;sort_by=TOTAL_EXEC_TIME/executed?project=alien-paratext-461204-i9)
- **GCE VM**：[dev-instance](https://console.cloud.google.com/compute/instancesDetail/zones/asia-southeast1-a/instances/dev-instance)
- **反向代理**：nginx（详见 `nginx/README.md`）
- **API endpoint**：https://app.inty.cc
  - Monitoring：https://app.checklyhq.com/accounts/1896e6d6-1599-414f-998e-3dabcc58fd7f
- **Inty-dev**：https://dev.inty.sxwl.ai
  - 运营评测工具：https://dev.inty.sxwl.ai/evaluation

### iMate（第二 Inty 后端实例）Cloud SQL 逻辑库

**完整步骤（含 gcloud、GCS、VM、DNS）**：[docs/OPS_IMATE_INTY_DEPLOY_GCLOUD.md](../docs/OPS_IMATE_INTY_DEPLOY_GCLOUD.md)。

与 IntelliMate 共用 Cloud SQL 实例 `inty-prod`（私网 IP 与现网 `database.host` 一致），**新增独立逻辑库**（方案 A，见 [docs/DEVOPS_IMATE_BACKEND_PLAN.md](../docs/DEVOPS_IMATE_BACKEND_PLAN.md)）。在可连该实例的客户端执行（示例库名与 [config.yaml.imate_dev](config.yaml.imate_dev) / [config.yaml.imate_prod](config.yaml.imate_prod) 一致）：

```sql
CREATE DATABASE "inty-imate-dev";
CREATE DATABASE "inty-imate";
```

`postgres` 超级用户默认可连接新库；若使用独立角色，需 `GRANT ALL PRIVILEGES ON DATABASE ...`。

逻辑库创建后，在**指向 iMate 库**的配置上执行 Alembic（勿用 IntelliMate 的 `config.yaml.dev`/`prod` 误连）：

```bash
export PYTHONPATH=.
alembic -c alembic/alembic.ini -x config=devops/config.yaml.imate_dev upgrade head
# prod
alembic -c alembic/alembic.ini -x config=devops/config.yaml.imate_prod upgrade head
```

**GCS**：在 GCP 控制台创建与配置中一致的 bucket（`imate-static-dev`、`imate-static-prod`），为 iMate 后端服务账号配置对象读写权限；勿与 IntelliMate `inty-static` 混用。

**GCE / nginx**：宿主机端口与域名见 `devops/README.md` 中 iMate 小节；TLS 需为新域名跑 Certbot 后再 `nginx -t` / reload。

### 日志

- Cloud logging：prod container streaming logs https://cloudlogging.app.goo.gl/o8QRPguGe78soGUY9
- 使用 docker `gcplogs` driver（概念与选项参考）：https://docs.docker.com/engine/logging/drivers/gcplogs/

### 其它外部依赖/平台账号（便于排查）

- CloudFlare：`it@sxwl.ai`（图片裁切/缩放/压缩等）
- LangSmith：`try@sxwl.ai`
- OpenRouter：`it@sxwl.ai`
- ElevenLabs：`it@sxwl.ai`

## DataStream + CloudSQL

- Network attachment
  - <img width="1904" height="752" alt="image" src="https://github.com/user-attachments/assets/a32f0f9b-665b-4271-b150-6d9725ce16bb" />
- Private network connectivity: VPC peering
- <img width="1320" height="1602" alt="image" src="https://github.com/user-attachments/assets/757063e7-a218-42cf-a084-60345a8e1c89" />
