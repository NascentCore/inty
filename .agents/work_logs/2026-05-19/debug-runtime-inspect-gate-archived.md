# 封存：DEBUG 门控 companion_runtime_inspect（暂不合并 main）

`INTY_RUNTIME_MODE`（`start.sh --debug` → DEBUG，否则 PROD）下仅在 DEBUG 暴露 `companion_runtime_inspect`、zip 落盘与对应 prompt；PROD 禁止向用户透露内部运行机制。

## 恢复方式

- **分支**：`cursor/debug-runtime-inspect-gate-826e`（远端已推送）
- **归档标签**：`archive/debug-runtime-inspect-gate-826e-2026-05-19` → commit `b504cf7c4`
- **PR（未合并，可关闭或保留草稿）**：https://github.com/NascentCore/inty/pull/3122

```bash
git fetch origin
git checkout cursor/debug-runtime-inspect-gate-826e
# 或：git checkout archive/debug-runtime-inspect-gate-826e-2026-05-19
```

## 已实现要点（相对当时 main）

- `app/core/companion_harness/runtime_mode.py`、`backend/ops/start.sh`
- 工具：`companion_tool_runtime` DEBUG 门控、`runtime_inspect_tool` + `runtime_inspect_zip_export.py`
- Prompt：`TOOLS.runtime_inspect.md`（DEBUG 注入）、`system_messages.py` 内联 DEBUG/PROD 条款
- 测试：`test_runtime_mode.py`、`test_build_openai_repl_tools_runtime_mode.py`、`test_companion_runtime_inspect_tool.py`

## 后续待办（若重新拾起）

- 与 main 再次 `merge origin/main` 并跑 backend CI
- 产品确认 PROD 禁透露边界是否仍要保留全文案
- 可选：将 `prompts/contracts/` 外置方案保持删除（已简化为内联）
