# backend/ops（运营平台）

- Ops 提供 evaluation Web UI 与完整 `/api/v1`（evaluation、festival_memory + 与 Android 共用的 shared 端点）。
- 启动：`./backend/ops/start.sh [--local|--dev] [--debug] [--log-file PATH]`（`--local`/`--dev` 等价；`--debug` 打开 DEBUG；`--log-file` 写文件；**同时** `--debug` 与 `--log-file` 时终端为 INFO、文件为 DEBUG，等价于 `INTY_CONSOLE_LOGGING_LEVEL=INFO`）。任意入口也可设 `INTY_LOG_FILE`；手动分流见 `app/core/logging.py` 的 `INTY_CONSOLE_LOGGING_LEVEL`。
- 部署域名：ops.inty.cc（prod）、dev.ops.inty.cc（dev）；部署方式见计划与 [backend/README.md](../README.md)。
