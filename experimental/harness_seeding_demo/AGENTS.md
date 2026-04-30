# harness_seeding_demo

- **禁止**修改 `app/core/agentic_kernel/`；试验代码仅在本目录（及后续你批准的依赖）内编写。
- 推理调用通过既有公开入口链：`CompanionManager` / `run_turn`（或 `tools/inty_v2_repl` 对其薄封装），详见根目录 [README.md](README.md)。
- 新增产物优先：`seeds/`（静态 workspace 模板）、`scorer/`（外部判定）、`scripts/`（批跑与报表）。
