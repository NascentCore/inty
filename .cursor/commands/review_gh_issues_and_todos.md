# Review GitHub Issue & TODO

## 分工

| 载体 | 用途 | 语言 |
|------|------|------|
| **GitHub issue** | 背景、范围、验收、依赖 | 简体中文 |
| **代码 TODO** | 改哪里、指向哪个 issue | 英文 |

- 大 & 复杂 → Epic + 子 issue
- 小改动 → 代码 TODO（agent 可自动拾取）
- **不要**在 `AGENTS.md` 或 skills 里引用 issue

## 审 Issue（5 项）

1. **结构** — Epic 与子 issue 不重叠；Epic 表不含自己
2. **术语** — 与代码一致（如 `INACTIVE` vs `SEALED`）；scope = acceptance
3. **依赖** — 产品 blocks 后端；`identity → bond → provisioning`
4. **Labels** — 域 + triage 正确（产品 → `chat`；工程 → `agentic_companion`）
5. **锚点** — issue body 路径 = repo 里实际 TODO

---

## 审代码变更

- 删 doc 后，`DESIGN.md` 等是否改链到 issue
- TODO 指向**子 issue**，不只挂 Epic
- 纯 TODO/文档 diff → 查追踪漂移即可，不必强求测试

---

## 修补优先级

| 级别 | 内容 |
|------|------|
| **P0** | 术语对齐、blocked-by、scope 拆分、易混 issue 号（如 #3396 ≠ #3696） |
| **P1** | Epic 索引、锚点表、同步代码 TODO |
| **P2** | Epic maintenance comment、triage 批量更新 |
