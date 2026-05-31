# Epics and GitHub Projects

跨多条 issue、跨模块、跨季度的计划用 **Epic 母 issue** 组织；需要看板/进度时用 **GitHub Project**。

## 何时建 Epic

- ≥3 条 open issue **共享同一架构决策或同一用户可见里程碑**
- PRD / 路线图描述的工作 **无法在一个 vertical slice 内交付**
- Audit 报告 `coupled` 分类下的 issue 群

不必建 Epic：单条可独立 merge 的 bug；已有明确 parent PRD issue 且子 slice 已互链。

## Epic 母 issue 约定

**标题**：`[Epic] <域> — <简短主题>`，例：`[Epic] agentic_companion — bootstrap 体验重构`

**Labels**：域 label + `enhancement` + 一个 `p*`（通常 `p1` 或 `p2`）。母 issue **不要** 标 `ready-for-agent`（它是跟踪壳，不是 implementation ticket）。

**Body 模板**：

```markdown
## Goal

One paragraph: user-visible outcome when all children are done.

## Child issues

- [ ] #123 — slice title
- [ ] #124 — slice title

## Non-goals

- …

## Architecture / decisions

Links to ADR or decisions made in grilling.

## Status

Last updated YYYY-MM-DD: …
```

**子 issue**：body 含 `## Parent` → `#<epic>`；母 issue 的 checklist 与子 issue 号保持同步（act 时双向更新）。

## GitHub Project（长期路线图）

适合：季度级 roadmap、跨 `agentic_companion` + `android` + `backend` 的协调。

```bash
# 列出已有 projects（owner = org/user）
gh project list --owner nascentcore

# 创建 project（需 maintainer 确认名称）
gh project create --owner nascentcore --title "Companion harness 2026 H1"

# 把 issue 加入 project（project number 来自 list）
gh project item-add <project-number> --owner nascentcore --url https://github.com/nascentcore/inty/issues/123
```

**约定**：

- Project **列** 建议：`Backlog` → `Ready` → `In progress` → `Done`（与 triage label 对齐：`ready-for-agent` 进 `Ready`）
- 每条 Epic 母 issue **至少** 对应 Project 里一行；子 issue 可挂同一 Epic 分组或单独卡片
- Project 描述里链到 Epic 母 issue `#N`

## 与 `/to-issues` 协作

1. Epic 母 issue 或 PRD issue 作为 **plan 源**
2. 运行 `/to-issues` 切 vertical slice → 得到子 issue 列表
3. 本 skill **act** 阶段：创建子 issue、更新 Epic checklist、close 被合并的旧重复条

## 关闭 Epic

当 **所有** child checklist 完成（子 issue closed 或 merged）：

1. Epic body `## Status` 写总结
2. `gh issue close <epic>`，comment 链到关键 PRs
3. 从 Project 移到 `Done` 或 archive
