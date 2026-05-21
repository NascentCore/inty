# `.cursor/skills/`：可复用操作手册（Skills）

**一句话**：把 **易错的多步流程**（本地 CI、LangSmith 导出、Alembic、后端排障等）沉淀成 **人类与智能体共用的小抄**；每个 SKILL 指向 **脚本或命令** 而非重复粘贴大段 shell。

## 维护方式

- 若某技能需要 **可执行 helper**，优先把脚本落在 [`.cursor/skills/scripts/`](/.cursor/skills/scripts/)，在 SKILL 里 **链接与说明参数**。
