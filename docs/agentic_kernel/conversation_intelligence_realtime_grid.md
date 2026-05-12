# Conversation grid: intelligence vs realtime

Axes: x = 弱智能 / 适中 / 强智能 (columns); y = 慢实时 / 适中实时 / 快实时 (rows). Top row labels the x-axis; left column labels the y-axis.

**Figure (matplotlib + YAML):** regenerate with

```bash
python3 scripts/draw_labeled_grid.py \
  docs/agentic_kernel/conversation_intelligence_realtime_grid.yaml \
  -o docs/agentic_kernel/conversation_intelligence_realtime_grid.png
```

Source data: [conversation_intelligence_realtime_grid.yaml](/docs/agentic_kernel/conversation_intelligence_realtime_grid.yaml). Skill: [.cursor/skills/conversation-grid-matplotlib/SKILL.md](/.cursor/skills/conversation-grid-matplotlib/SKILL.md).

![conversation intelligence realtime grid](conversation_intelligence_realtime_grid.png)

## See also

- [IDEAS.md](IDEAS.md)：记忆管线、实验目录收口等条目与网格轴上的能力选型相关。
- [ARCH.md](ARCH.md)：伴侣 `/api/v1/chat/ws`、`MemoryStore`、`run_turn` 等当前实现边界。
