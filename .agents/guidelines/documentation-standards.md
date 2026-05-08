# 文档层次与工程文档维护

摘自 [`/AGENTS.md`](/AGENTS.md) 中「文档层次结构」「工程文档维护」两节。

## 文档层次结构

- **最高层（面向人类读者）**：必须交代完整概念与适用边界；用约三分之一页纸篇幅做总体描述，使人一眼能判断「这是什么、和谁相关、要不要往下读」。人的注意力窗口有限，缺少这一层易导致误判优先级或读不下去。
- **中间层（仍面向人）**：按需展开：目录职责、如何运行、接口与约定、常见问题等；可分段、可链接到更细文档。
- **最底层（源码与实现细节）**：代码内注释、模块 docstring、PR/commit 中的实现说明等，主要给编码智能体与维护者阅读；详略由编写者按上下文自行判断，不以「人类扫读一整 repo」为第一约束。

## 工程文档维护

- Markdown 引用本仓库内文件时，使用从仓库根目录起的绝对路径（以 `/` 开头），例如 `/app/api/AGENTS.md`、`/AGENTS.md`；不要使用 `../../app/api/AGENTS.md` 这类相对路径。
- In markdown, reference in-repo files with repo-root absolute paths (leading `/`), e.g. `/app/api/AGENTS.md`; do not use `../../...` relative paths.
- 当进行改动时，如变更足够重要且会影响相应目录的 `AGENTS.md` 指南、及其他 markdown 文件，请同步更新该目录下的 `AGENTS.md`、及其他 markdown 文件。
- 新功能/需求开发对应的文档应该添加 FR_ 前缀，如 docs/FR_CHAR_BOOSTING.md
