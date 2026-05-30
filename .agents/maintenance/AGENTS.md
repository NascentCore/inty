# `.agents/maintenance/`：维护任务看板

非紧急但需持续推进的仓库卫生工作拆成 **可拾取的 Markdown 任务卡**，供编码智能体按优先级认领。

## 文件约定

- **命名**：文件名里带优先级与主题，例如 `p1_enhance_tests.md`。
- **结构**：每个任务文件内是 **TODO 列表**；智能体以 **单条 TODO** 为工作单元。
- **迭代**：完成一部分后更新同文件，让后来者看到 **剩余块**；若需对照 `main` 的增量，可用仓库技能 **git-file-last-commit** 辅助。

## 例行任务

- looking for files that can be deleted and delete them.
- Keep only at most 9 tasks, and remove the least important one from this dir.
