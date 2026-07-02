<!-- CREATED_BY_AGENT -->

# 2026-07-02：容器日志改 VM 本地、记录部署态、停止 inty-backend-dev

## 动机

降低 GCP Cloud Logging 账单；IntelliMate 容器 stdout 留在 VM（Docker 默认 `json-file`）。

## 已执行变更

1. **VM**：重建 `inty-backend-{dev,prod}`、`inty-ops-{dev,prod}`，去掉显式 log driver（使用 Docker 默认）。
2. **CI**：`.github/workflows/build_and_deploy_{backend,ops,push_worker}.yml` 同步去掉 `--log-driver=gcplogs`（commit `5c1bbf3c2`）。
3. **运维决策**：`inty-backend-dev` 手动 `docker stop`（无活跃使用）；`inty-push-worker-{dev,prod}` 保持停止。
4. **文档/脚本**：删除 `devops/fetch_inty_container_logs.sh`；现状见 [DEPLOYMENT_STATE.md](../DEPLOYMENT_STATE.md)。

## 捕获态（2026-07-02）

### 运行中

| 容器 | Image digest | Host port |
|------|--------------|-----------|
| inty-backend-prod | `...@sha256:afdef1b7775742771c55218276232fd5b89cf7a14a470e9407382e28b808b690` | 8100 |
| inty-ops-prod | `...@sha256:82b0c28435280fdb2f52e2a435c614ef29b544f0a15887599f714de6e5b86e51` | 8101 |
| inty-ops-dev | `...@sha256:1675cf18638828e019abd0a919479a754f054e426a9e9bc488e38fa725134430` | 8001 |

### 已停止

- `inty-backend-dev`：entrypoint 覆盖见 [DEPLOYMENT_STATE.md](../DEPLOYMENT_STATE.md)
- `inty-push-worker-dev` / `inty-push-worker-prod`：未重建；重启前须经 CI 部署

## 启动 inty-backend-dev

```bash
ssh inty 'sudo docker start inty-backend-dev'
# 或按 DEPLOYMENT_STATE.md 中的 entrypoint 覆盖完整 docker run
```

## 相关文档

- 现状索引：[DEPLOYMENT_STATE.md](../DEPLOYMENT_STATE.md)
- Alembic compat（prod 仍适用）：[2026-06-19-inty-pg-alembic-compat-prod.md](./2026-06-19-inty-pg-alembic-compat-prod.md)
