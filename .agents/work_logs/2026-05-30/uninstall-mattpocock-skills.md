# 卸载 mattpocock/skills

人类队友（2026-05-30）：要求卸载此前安装的 [mattpocock/skills](https://github.com/mattpocock/skills)（见 [2026-05-25 defer-setup](/.agents/work_logs/2026-05-25/mattpocock-skills-defer-setup.md)）。

## 行动要点

- 删除 `.agents/skills/` 下全部 14 个 mattpocock skill（caveman、diagnose、grill-me、grill-with-docs、handoff、improve-codebase-architecture、prototype、setup-matt-pocock-skills、tdd、to-issues、to-prd、triage、write-a-skill、zoom-out）。
- 删除根目录版本锁 `skills-lock.json`。
- 更新根 `AGENTS.md` 的 `## Agent skills` 小节：只保留 Inty 自有 skill（`.cursor/skills/`）说明，移除 mattpocock 安装与 setup 状态描述。

## 备注

- Inty 自有 skill（`.cursor/skills/`）未改动。
- 保留 2026-05-25 旧日志（append-only），不改写历史。
