---
name: companion-harness-dead-code-cleanup
description: >-
  Run vulture (--min-confidence 80) for unreferenced functions/constants and
  ruff --select F401 --fix to remove unused imports, scoped to companion-harness
  trees only (not legacy app/). Use when cleaning dead code in companion_harness,
  living_sphere, techno_core, agentic_companion/channel, or related tests.
---

# Companion harness dead-code cleanup

Generated entirely by Cursor agent.

在 **companion harness 允许范围** 内做静态清理：**ruff** 自动删未使用 import；**vulture** 列出高置信度未引用 function / constant，需人工确认后再删。

**禁止** 扫描 legacy / maintenance 代码（例如 `live_chat_service`、非 `/api/v1/chat/ws` 的旧聊天路径、整个 `app/` 树）。

## 范围（allowlist）

脚本 [`.cursor/skills/scripts/companion_harness_dead_code_cleanup.py`](../scripts/companion_harness_dead_code_cleanup.py) 仅处理：

- `app/core/companion_harness/`
- `app/living_sphere/`、`app/techno_core/`
- `app/schemas/chat_websocket.py`
- `app/services/agentic_companion/`、`app/services/agentic_channel/`、`companion_chat_service.py`
- `app/api/v1/endpoints/chat_ws*.py`
- `backend/ops/weixin_channel/`、`telegram_channel/` 及相关 ops API
- `tests/app/core/companion_harness/`、`tests/living_sphere/`

## 前置

仓库根目录、已激活 `.venv`（脚本通过当前 Python 调用 `python -m ruff` / `python -m vulture`）：

```bash
source .venv/bin/activate
uv sync --group dev   # 或: pip install ruff vulture
python .cursor/skills/scripts/companion_harness_dead_code_cleanup.py
```

等价于依次执行：

1. `ruff check --select F401 --fix <scope paths>`
2. `vulture <scope paths> --min-confidence 80`

### 参数

- `--no-fix-imports`：只跑 vulture，不改 import
- `--no-report-dead`：只跑 ruff F401 fix
- `--vulture-whitelist PATH`：动态引用白名单（pytest fixture、`__getattr__` 导出等）
- `--repo-root DIR`：非 cwd 时指定仓库根

## Agent 工作流

1. **跑脚本**（默认两项都开）。
2. **提交 ruff 改动**：未使用 import 可安全自动删除；检查 diff 后 `git add` 相关文件。
3. **审阅 vulture 输出**（exit code 1 表示有命中，非工具失败）：
   - 确认非反射 / 字符串动态导入 / 测试间接引用
   - 误报写入 whitelist 或就地 `# noqa`（vulture 约定）
4. **删确认的死代码**（function、constant、整模块），勿动 legacy 目录。
5. **回归**：`pytest tests/app/core/companion_harness tests/living_sphere`（或受影响子集）。

## vulture 注意

- `--min-confidence 80` 只保留高置信度项，降低误报。
- 常见误报：仅被测试通过字符串调用的符号、ORM / Pydantic 字段、协议 `__init__.py` 重导出。
- 生成初始 whitelist：`vulture <path> --make-whitelist > whitelist.py`，再 `--vulture-whitelist whitelist.py`。

## 与 CI 的关系

本 skill **不** 接入 CI gate；清理由人工或 agent 会话触发。层边界检查仍用 `check_layer_dependencies.py`。
