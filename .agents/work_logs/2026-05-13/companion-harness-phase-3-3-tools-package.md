# Phase 3.3：companion_harness `tools/` 拆包

- `git mv`：`companion/` 下工具契约、执行、后台线程、路由、OpenAI prepare、读网页/搜索、生图 gate、runtime inspect 等模块迁入 `app/core/companion_harness/tools/`；原 `tools.py` 重命名为 `companion_tools.py` 以避免与包名 `tools` 混淆。
- 新增 `tools/__init__.py` 包级 docstring（无功能性代码）；`tool_background` / `runtime_inspect_*` 等对 `companion` 的依赖改为绝对 import；保留既有 `tools/runtime.py`、`registry.py`、`dispatchers/`。
- 测试：`tests/app/core/companion_harness/tools/` 迁移 Phase 3.3 所列用例；`chat.py` 与仍留在 `companion/` 的测试更新 import。
- 文档：`docs/companion_harness/ARCH.md`、`todos/COMPANION_HARNESS_USER_MODEL.md` 中 `tool_background.py` 路径更新。
- 验收：`uv run pytest tests/app/core/companion_harness/tools/ …`（含 bootstrap / prompt_stack / turn_async_dual / websocket_coordinator）86 passed。
