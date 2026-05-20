---
name: release-preview-version
description: >-
  Write a minimal daily iMate companion-harness preview under docs/imate/previews/YYYY-MM-DD.md
  (New features, Changed features, Expected results in REPL) and update previews AGENTS.md Latest link.
  Use when releasing preview, imate preview, daily preview, or docs/imate/previews.
---

# release-preview-version

## When to use

- 用户要发 **日更 preview**、更新 `docs/imate/previews/`、或记录 REPL 可测的 harness 变更。

## Before writing

1. 读 [`docs/imate/previews/AGENTS.md`](../../../docs/imate/previews/AGENTS.md)。
2. 确认在 **main**（`git branch --show-current`）；不在 main 则先告知用户。

## Steps

1. `preview_date` = 用户指定或 `date +%Y-%m-%d`；目标 `docs/imate/previews/${preview_date}.md`。
2. 若该文件已存在：询问是否覆盖。
3. **上一版**：同目录 `*.md` 中 ISO 日期最大且 `< preview_date` 的文件；读 YAML `git_commit` → `PREV_COMMIT`。无上一版则 `previous_preview: null`，Changed = `None`，New = 当日用户可见 baseline（仅首版）。
4. `git rev-parse HEAD` → `git_commit`。
5. 有上一版时：`git log ${PREV_COMMIT}..HEAD --oneline -- app/core/companion_harness/ tools/inty_v2_repl/ app/api/v1/endpoints/chat.py app/schemas/chat_websocket.py`；筛 **用户可见** 项填入 **New features** / **Changed features**；为每条写 **Expected results in REPL**（metadata label、`image-url:`、`[SILENT]` 等）。细节见 [`inspect-repl-message-metadata`](../inspect-repl-message-metadata/SKILL.md)。
6. 写当日 md（YAML + 三节）；更新 [`AGENTS.md`](../../../docs/imate/previews/AGENTS.md) 顶部 `**Latest preview:**` 链接。
7. 回复：文件路径、`git_commit`、New/Changed 条数；跑 REPL 见 [`launch-inty-backend`](../launch-inty-backend/SKILL.md)。

## Do not

- 添加 `README.md`、`_TEMPLATE.md`、`git_branch`、第四节以后的长文。
- 复制 [`COMPANION_WS_RUNBOOK.md`](../../../docs/companion_harness/COMPANION_WS_RUNBOOK.md) 全文。
