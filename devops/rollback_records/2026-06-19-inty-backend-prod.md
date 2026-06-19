<!-- CREATED_BY_AGENT -->

# inty-backend-prod rollback record: 2026-06-19

This file records the currently running production `inty-backend-prod` container before deploying a newer version, so the old setup can be restored if the new deployment breaks.

## Captured container

- Captured at: `2026-06-19T07:47:56Z`
- Container: `inty-backend-prod`
- Container ID: `328283d1971406ae0d2fde67876e50bd1d03bfedcfacae289ffbee0e660f8ba4`
- State at capture time: `running`
- Created at: `2026-05-19T07:05:31.480973876Z`
- Command: `/start.sh`
- Working directory: `/`
- Restart policy: `unless-stopped`
- Network mode: `bridge`

## Image to restore

- Immutable remote image: `ghcr.io/nascentcore/inty-backend/inty-server@sha256:27f08f65828e3873fd7026cb09ecc6f90591bac43b5ca631dc0ccdcec4ea1d5b`
- Local image ID at capture time: `sha256:070e97ca088e3eb3e1879fa97e3918d5821d9e155f667e5cb6ba0505588975c9`
- Local rollback tag created at capture time: `inty-backend-prod-rollback:20260619T0746Z-4a7c0a98`
- VCS revision label: `4a7c0a98abe50a20063081aee466c87353652f25`

## Runtime setup

- Port mapping: host `8100` to container `8000/tcp`
- Bind mounts:
  - `/opt/inty-prod/inty-backend-key.json` to `/inty-backend-key.json`
  - `/opt/inty-prod/inty-firebase-key.json` to `/inty-firebase-key.json`
- Docker labels:
  - `application=inty-backend`
  - `environment=prod`
  - `org.opencontainers.image.revision=4a7c0a98abe50a20063081aee466c87353652f25`
- Docker log driver: `gcplogs`
- Docker log labels: `application,environment`
- Environment keys present:
  - `LANGCHAIN_TRACING_V2`
  - `LANGCHAIN_PROJECT`
  - `LANGCHAIN_API_KEY`
  - `PYTHONPATH`
  - `INTY_VCS_REVISION`
  - `INTY_BUILD_TIME`
  - `INTY_VCS_DIRTY`
  - Base Python image keys: `PATH`, `LANG`, `GPG_KEY`, `PYTHON_VERSION`, `PYTHON_SHA256`

## Restore command

Use this only when intentionally reverting production after a broken deployment.

```bash
docker pull ghcr.io/nascentcore/inty-backend/inty-server@sha256:27f08f65828e3873fd7026cb09ecc6f90591bac43b5ca631dc0ccdcec4ea1d5b

docker run --detach \
  --name inty-backend-prod \
  --restart unless-stopped \
  --log-driver gcplogs \
  --log-opt labels=application,environment \
  --label application=inty-backend \
  --label environment=prod \
  --label org.opencontainers.image.revision=4a7c0a98abe50a20063081aee466c87353652f25 \
  --publish 8100:8000 \
  --volume /opt/inty-prod/inty-backend-key.json:/inty-backend-key.json \
  --volume /opt/inty-prod/inty-firebase-key.json:/inty-firebase-key.json \
  ghcr.io/nascentcore/inty-backend/inty-server@sha256:27f08f65828e3873fd7026cb09ecc6f90591bac43b5ca631dc0ccdcec4ea1d5b
```

If the remote digest is unavailable but the local image was not pruned, use `inty-backend-prod-rollback:20260619T0746Z-4a7c0a98` in the final command instead of the remote digest.

## 2026-06-19 部署时间线（摘要）

1. **07:47 UTC** — 捕获上表 `4a7c0a98` 运行态（本文件）。
2. 部署 main **`6c46b2f8c`** — release IntelliMate（`64615013`）出现聊天 UI 不刷新等问题；当前镜像打本地 tag `inty-backend-prod-broken:20260619T0757Z-6c46b2f8c` 备查。
3. **回滚** 至 `4a7c0a98` 镜像，prod 恢复。
4. 创建分支 **`intellimate-client-compat-local-postgres-prod`**（`4a7c0a98` + local Postgres devops only）。
5. 本地 `inty` 曾处于 main Alembic head → compat 部署启动失败；见 [Alembic compat 记录](./2026-06-19-inty-pg-alembic-compat-prod.md)。

## Related

- [inty 逻辑库 Alembic 与 compat prod 后端不一致](./2026-06-19-inty-pg-alembic-compat-prod.md) — local Postgres `inty` migration 版本与 compat 分支部署的约束
