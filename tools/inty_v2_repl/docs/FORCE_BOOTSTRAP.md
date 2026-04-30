# 关于 BOOTSTRAP（仅后端 WebSocket 模式）

本 CLI 的 `repl` **只**连接 Inty 后端的 `/api/v1/chat/ws`（见 `tools/inty_v2_repl/main.py`）。**不再有**本地磁盘上的 agentic `bootstrap-agent` / `run_workspace_bootstrap_loop` 流程。

- **首次对话 / onboarding**：由 **Inty 后端与线上数据** 决定（含服务端 bootstrap），不在本仓库的 REPL 进程里强制落盘 companion 五件套。
- **本地 `--workspace` 目录**：仅用于 **进程日志**（如 `inty_v2.log`）等本地输出，不是对话权威存储。

联调步骤见 [GET_STARTED.md](GET_STARTED.md)（启动后端、`INTY_ACCESS_TOKEN`、`--agent-id` / `INTY_V2_CHAT_AGENT_ID`、`python -m tools.inty_v2_repl.main repl ...`）。

若需研究历史上「本地 workspace + `templates/BOOTSTRAP.md`」的实现，请查看 git 历史中已删除的 `bootstrap-agent` / `init-workspace` 与 `workspace_init_loop.py` 调用方（当前仍保留 `workspace_init_loop` 等模块供其它单元测试与 kernel 联调使用，但 **CLI 不再暴露**）。
