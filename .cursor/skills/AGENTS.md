# `.cursor/skills/`：可复用操作手册（Skills）

## 维护方式

- 若某技能需要 **可执行 helper**，优先把脚本落在 [`.cursor/skills/scripts/`](/.cursor/skills/scripts/)，在 SKILL 里 **链接与说明参数**。

## mattpocock/skills 说明

mattpocock/skills 已安装于 `.agents/skills/`（`skills-lock.json`）；Inty 自有 skill 在 `.cursor/skills/`。

### Setup 状态

**暂不运行** `/setup-matt-pocock-skills`：人类队友要先试用 skill。

在未 setup 前，`docs/agents/` 不存在；依赖该目录的 engineering skill（`to-issues`、`to-prd`、`triage` 等）缺少本仓库上下文。productivity skill 与部分 engineering skill 可直接试用。
