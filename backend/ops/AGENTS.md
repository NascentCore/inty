# backend/ops（运营平台）

- Ops 提供 evaluation Web UI 与完整 `/api/v1`（evaluation、festival_memory + 与 Android 共用的 shared 端点）。
- 启动：`./backend/ops/start.sh [--dev|--test]`，默认端口 8001；Cloud Run 使用 `PORT`（默认 8080）。
- 部署域名：ops.inty.cc（prod）、dev.ops.inty.cc（dev）；部署方式见计划与 [backend/README.md](../README.md)。
- **Follow-up**：ops 上线并验证后，从主应用移除 evaluation/festival_memory 挂载与 re-export 模块，见 [TASKS.md](../../TASKS.md)（ops 平台任务）。
