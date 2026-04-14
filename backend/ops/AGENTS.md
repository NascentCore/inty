# backend/ops（运营平台）

- Ops 提供 evaluation Web UI 与完整 `/api/v1`（evaluation、festival_memory + 与 Android 共用的 shared 端点）。
- 启动：`./backend/ops/start.sh [--local|--dev]`（两标志等价），默认端口 8001；Cloud Run 使用 `PORT`（默认 8080）。
- 部署域名：ops.inty.cc（prod）、dev.ops.inty.cc（dev）；部署方式见计划与 [backend/README.md](../README.md)。
