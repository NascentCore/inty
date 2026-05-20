# iMate preview releases（REPL 日更）

**Latest preview:** [2026-05-19](2026-05-19.md)

每日在 **main** 上追加 `YYYY-MM-DD.md`，供评估者用 terminal REPL 验证 companion harness（`/api/v1/chat/ws`）。

## 环境

- 启动后端：[`launch-inty-backend`](../../../.cursor/skills/launch-inty-backend/SKILL.md)
- 运行 REPL：[`tools/inty_v2_repl/AGENTS.md`](../../../tools/inty_v2_repl/AGENTS.md)
- 解读 metadata 行：[`inspect-repl-message-metadata`](../../../.cursor/skills/inspect-repl-message-metadata/SKILL.md)

## 单日文件格式

可选 YAML front matter（`preview_date`、`git_commit`、`previous_preview`）。

正文 **仅三节**（短 bullet，关键术语保留英文）：

1. **New features** — 本版新增、REPL 可观察或触发。
2. **Changed features** — 相对上一版 preview 的行为变化；无则 `None`。
3. **Expected results in REPL** — 与上面对应：在 REPL 里应看到什么（label、`image-url:`、`[SILENT]` 等）。

发布流程：[`release-preview-version`](../../../.cursor/skills/release-preview-version/SKILL.md)。
