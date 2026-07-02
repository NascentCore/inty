<!-- CREATED_BY_AGENT -->

# IntelliMate VM 部署现状（`inty` GCP VM）

**最后核对**：2026-07-02（`ssh inty` + `docker ps` / `docker inspect`）。变更记录见 [rollback_records/2026-07-02-disable-gcplogs-and-vm-state.md](rollback_records/2026-07-02-disable-gcplogs-and-vm-state.md)。

## 运行中服务

| 容器 | 状态 | 宿主机端口 | 公网 URL | 日志驱动 |
|------|------|------------|----------|----------|
| `inty-backend-prod` | running | 8100 → 8000 | https://app.inty.cc/ | `json-file`（Docker 默认） |
| `inty-ops-prod` | running | 8101 → 8001 | https://ops.inty.cc/ | `json-file` |
| `inty-ops-dev` | running | 8001 → 8001 | https://dev.ops.inty.cc/ | `json-file` |
| `inty-pg` | running | 5432 → 5432 | （仅 VM 内） | `json-file` |

## 已停止（有意保留容器，不删）

| 容器 | 状态 | 说明 |
|------|------|------|
| `inty-backend-dev` | stopped | 当前无活跃使用；`dev.inty.sxwl.ai` 经 nginx 会 502。镜像与配置保留，需要时 `docker start inty-backend-dev` |
| `inty-push-worker-dev` / `inty-push-worker-prod` | stopped | 推送 worker 未启用；重启前须经 CI 重新部署 |
| `inty-backend-imate-*` / `inty-ops-imate*` | stopped | iMate 实例，与 IntelliMate 并行规划；见 [imate/DEVOPS_IMATE_BACKEND_PLAN.md](imate/DEVOPS_IMATE_BACKEND_PLAN.md) |

## 日志

- VM 上：`sudo docker logs <container>`
- 从本机拉取：`devops/fetch_inty_vm_container_logs.sh <alias>`

## 镜像 digest（当前）

- `inty-backend-prod`：`ghcr.io/nascentcore/inty-backend/inty-server@sha256:afdef1b7775742771c55218276232fd5b89cf7a14a470e9407382e28b808b690`
- `inty-ops-prod`：`ghcr.io/nascentcore/inty-backend/inty-ops@sha256:82b0c28435280fdb2f52e2a435c614ef29b544f0a15887599f714de6e5b86e51`
- `inty-ops-dev`：`ghcr.io/nascentcore/inty-backend/inty-ops@sha256:1675cf18638828e019abd0a919479a754f054e426a9e9bc488e38fa725134430`
- `inty-backend-dev`（已停）：`ghcr.io/nascentcore/inty-backend/inty-server@sha256:1679f33c1d47ca0ff10eaf2fbaac6fcaa8e414ee438f0771f87dfc80cfa84574`

## 非默认启动配置（重建容器时须保留）

**`inty-backend-dev`**（已停）：绕过镜像内 `/start.sh`（避免 Alembic revision 冲突），直接起 uvicorn：

```bash
--entrypoint /bin/sh \
  ... \
  -c "python -m uvicorn backend.inty.main:app --host 0.0.0.0 --port 8000"
```

**`inty-backend-prod`**：compat 分支镜像的 `/start.sh` 需跳过 Alembic；挂载 VM 上已合并 main 的脚本：

```bash
--env INTY_SKIP_ALEMBIC_UPGRADE=1 \
--volume /tmp/inty-backend-start.sh:/start.sh:ro \
```

`/tmp/inty-backend-start.sh` 内容与仓库 [backend/inty/start.sh](../backend/inty/start.sh) 一致（含 `INTY_SKIP_ALEMBIC_UPGRADE` 判断）。未来 prod 镜像 digest 更新且内置 `start.sh` 已含该逻辑后，可去掉此 bind mount。

**`inty-backend-prod` 完整重建示例**（密钥与 LangSmith 值以 VM 为准）：

```bash
sudo docker run --detach \
  --name inty-backend-prod \
  --restart unless-stopped \
  --add-host=host.docker.internal:host-gateway \
  --env INTY_SKIP_ALEMBIC_UPGRADE=1 \
  --publish 8100:8000 \
  --env LANGCHAIN_TRACING_V2=true \
  --env LANGCHAIN_PROJECT=inty-backend-prod \
  --env LANGCHAIN_API_KEY=<from-existing-container-or-secrets> \
  --label application=inty-backend \
  --label environment=prod \
  --volume /opt/inty-prod/inty-backend-key.json:/inty-backend-key.json \
  --volume /opt/inty-prod/inty-firebase-key.json:/inty-firebase-key.json \
  --volume /tmp/inty-backend-start.sh:/start.sh:ro \
  ghcr.io/nascentcore/inty-backend/inty-server@sha256:afdef1b7775742771c55218276232fd5b89cf7a14a470e9407382e28b808b690
```

## CI 部署

- 工作流 `docker run` 不再指定 `--log-driver`（Docker 默认 `json-file`）。
- `workflow_dispatch` 选 `dev` 会 **stop/rm 并重建** `inty-backend-dev`；若希望 dev 后端保持停止，部署后需再执行 `docker stop inty-backend-dev`，或暂时勿对 dev 跑 backend workflow。

## 快速检查

```bash
ssh inty 'sudo docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
ssh inty 'for c in inty-backend-prod inty-ops-prod inty-ops-dev; do sudo docker inspect --format "{{.Name}} log={{.HostConfig.LogConfig.Type}}" $c; done'
```
