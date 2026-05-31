# Companion harness GitHub issue 组织（2026-05-31）

**一句话**：近期 `agentic_companion` 相关工作散落于 open PR、代码 TODO（#3113–#3211 未建 issue）与 paused PR；新增 5 个 epic + 18 个子 issue 的创建脚本统一入口。

## 背景

- Cloud Agent token 无 `issues:write`；#3200 等曾用 open PR 代 tracker。
- 5 月 companion 相关 open 项：`#3224` AUTONOMY、`#3237` feedback、`#3250` dreaming、`#3253` CI、`#3142`/`#3122` paused。
- 代码引用但缺失的 issue：`#3113`–`#3115`、`#3208`–`#3211`。

## Epic 结构

| Epic | 子 issue 数 | 覆盖 |
|------|------------|------|
| WebSocket transport & downlink | 4 | #3208–#3211 缺口、#3205 后续 |
| WS concurrency & turn scheduling | 4 | HoL、barge-in/supersede、#3253 |
| Inner-tick autonomy & subjective time | 4 | #3224/#3250、offline heartbeat |
| Memory, feedback & user model | 4 | #3237、user model、dual-envelope |
| Paused / non-mainline | 2 | #3142、#3122 |

## 执行

```bash
python3 .cursor/skills/scripts/create_companion_harness_issue_epics.py
python3 .cursor/skills/scripts/create_companion_harness_issue_epics.py --dry-run  # 预览
```

需 maintainer `gh` 具备 `issues:write`。Cloud Agent token **无** `issues:write` / `pull_requests:write`，无法在本环境直接 `gh issue create` 或 `gh pr edit`；issue 创建与 PR 描述更新均通过 **push 分支 commit** 完成。

创建后建议：给已有 open PR（#3224、#3237、#3250）comment 链到对应 epic；paused PR 加 epic 链接避免误拾取。
