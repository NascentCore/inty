# backend/ops（运营平台）

- Ops 提供 evaluation Web UI 与完整 `/api/v1`（evaluation、festival_memory + 与 Android 共用的 shared 端点）。
- 启动：`./backend/ops/start.sh [--local|--dev] [--debug] [--log-file PATH] [--build-frontend|--no-build-frontend]`（`--local`/`--dev` 等价；`--debug` 打开 DEBUG；`--log-file` 写文件；**同时** `--debug` 与 `--log-file` 时终端为 INFO、文件为 DEBUG，等价于 `INTY_CONSOLE_LOGGING_LEVEL=INFO`）。`--local` 下默认会先跑 `evaluation/build.sh`，`--no-build-frontend` 可跳过。`--local` 会将 `user-testing` 的 JWT 写入仓库根目录 `.inty_ops_bearer_token`（gitignore；路径可用环境变量 `INTY_OPS_BEARER_TOKEN_FILE` 覆盖），便于本地 smoke/REPL 读取而无需手抄 token。任意入口也可设 `INTY_LOG_FILE`；手动分流见 `app/core/logging.py` 的 `INTY_CONSOLE_LOGGING_LEVEL`。
- 本地端到端 smoke（例如 WebSocket `/api/v1/chat/ws`）：在仓库根执行 `scripts/inty_backend_smoke_tests/test_chat_ws.py`，设置 `INTY_API_BASE_URL=http://127.0.0.1:8001`（或 `--api-base`）；Bearer 一般不必手写 export，脚本会读 `.inty_ops_bearer_token`。说明见仓库 [.cursor/skills/inty-server-module-verify/SKILL.md](../../.cursor/skills/inty-server-module-verify/SKILL.md)。
- 部署域名：ops.inty.cc（prod）、dev.ops.inty.cc（dev）；部署方式见计划与 [backend/README.md](../README.md)。
