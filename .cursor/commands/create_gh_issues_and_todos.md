# Create GitHub issues and add TODOs

Create github issue(s) to track the work in current conversation,
and then add TODOs in appropriate code places (referencing the github issues) to tie the code with the created GitHub issue(s).

- Create TODOs for minor changes, they are picked up by the cursor automation.
- Create GitHub issues for large & complex follow-ups, also reference the issue in TODOs placed at appropriate code places.
- Do not reference issues in AGENTS.md or skills' MD files

- GitHub issues should be in Mandarin (中文简体）TODOs are in English for consistency
- When creating issues, apply labels to distinguish between other potential related issues, and increase structuredness.
- Make sure to reference issues in TODOs to allow agent to trace from code to github issues. GitHub issues serve as more complete background.

## Priority and severity

Follow [LABELS.md](/.cursor/skills/github-issue-consolidate/LABELS.md). Do not create new labels without maintainer approval.

## 创建 Issue

每条 issue 建议包含：

- `Parent: #xxxx`
- **目标** / **范围** / **验收**
- **依赖**（blocked by / blocks / depends on）
- **代码 TODO 锚点**（文件路径）

Epic 额外：

- 最小不变量
- 子 issue 索引（**不含 Epic 自身**）
- 建议实施顺序
- 进度说明（文档迁移、TODO 重定向）

**Labels**：只用 `gh label list` 已有 label；每条恰好一个 `p*`；新 label 需 maintainer 批准。

## 写 TODO

```python
TODO(tag-name): #1234 — short English description (epic #5678).
```

- 放在要改的 seam（onboard / restore / bond service 等）
- issue body 与代码 TODO **双向对齐**

```bash
rg '#1234|TODO\(' app/ backend/
```
