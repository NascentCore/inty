---
name: langsmith-inspect-companion-system-messages
description: >-
  Inspect companion LangSmith runs for duplicate or missing system messages in
  inputs.messages. Use when debugging SOUL/IDENTITY double injection, prompt
  stack, or verifying a trace after harness changes.
---

# LangSmith：检查 companion system messages

核对 LLM run 的 **`inputs.messages`** 中所有 **`role: system`** 块。

## 步骤

1. **下载 trace**（配置见 [`langsmith-download-run`](../langsmith-download-run/SKILL.md)）：

```bash
python .cursor/skills/scripts/download_run.py --trace-id "<TRACE_UUID>"
```

2. **选对子 run**（以 child 的 `inputs.messages` 为准）：
   - 用户可见回复 → `agentic_companion_chat`
   - 工具环 → `agentic_companion_tool_call`

3. **枚举并查重**（仓库根）：

```bash
python .cursor/skills/scripts/langsmith_inspect_system_messages.py \
  .inty/traces/<file>.json --run-name agentic_companion_chat
```

`DUPLICATE_BODIES` 或 `multiple soul-labeled` → 有重复；加 `--show-body` 看全文。

## 定因（常见）

| 现象 | 原因 |
|------|------|
| 两条 `# 灵魂档案`、正文相同 | DB 里 `IDENTITY.md` 与 `SOUL.md` 是同一份 → 查 [`inspect-companion-harness`](../inspect-companion-harness/SKILL.md) |
| 一条 soul + `TEMPLATE_REFERENCE SOUL.md` | 交互式 bootstrap 预期（未完成 `workspace_bootstrap_user_interactive_completed`） |
| tool span 多几块契约 | 正常；用 `--run-name agentic_companion_tool_call` 分开看 |

组装顺序真源：[`system_messages.py`](../../../app/core/companion_harness/companion/prompts/system_messages.py)（`build_system_messages`）。**SOUL 正常仅一条**（`bundle.soul`）。
