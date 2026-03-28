# TEST_STEPS_AGENTIC_PERSONIFIED_REPO_DESIGN

## 1. 测试目标

验证 `docs/FR_AGENTIC_PERSONIFIED_REPO_DESIGN.md` 已完整定义：

1. 人格化仓库的目标、边界与核心原则。
2. 可执行的自演进闭环（Observe -> Diagnose -> Propose -> Simulate -> Apply -> Verify -> Reflect）。
3. 可落地目录蓝图、治理门禁与分阶段路线。
4. 面向用户的 explain/guide/execute 三模式输出。

## 2. 成功标准

满足以下条件即通过：

1. 文档存在且标题正确。
2. 关键章节全部存在（目标、核心原则、人格模型、自演进闭环、治理边界、阶段路线、成功标准）。
3. 文档包含可落地目录蓝图（`repo_agent/`）。
4. 文档包含当前仓库的 next actions（最小落地建议）。

## 3. 测试命令与步骤

在仓库根目录执行：

1. `test -f docs/FR_AGENTIC_PERSONIFIED_REPO_DESIGN.md`
2. `rg "^## " docs/FR_AGENTIC_PERSONIFIED_REPO_DESIGN.md`
3. `rg "Observe -> Diagnose -> Propose -> Simulate -> Apply -> Verify -> Reflect" docs/FR_AGENTIC_PERSONIFIED_REPO_DESIGN.md`
4. `rg "^repo_agent/$|^  identity/$|^  runtime/$|^  governance/$" docs/FR_AGENTIC_PERSONIFIED_REPO_DESIGN.md`
5. `rg "^## 12\\. 对当前仓库的最小落地建议（Next Actions）" docs/FR_AGENTIC_PERSONIFIED_REPO_DESIGN.md`

## 4. 预期结果

1. 文件存在检查返回退出码 0。
2. `##` 章节列表含 1~12 章关键标题。
3. 闭环字符串匹配成功且仅用于主闭环定义。
4. 目录蓝图中的 `repo_agent/identity/runtime/governance` 均可匹配。
5. Next Actions 标题匹配成功。
