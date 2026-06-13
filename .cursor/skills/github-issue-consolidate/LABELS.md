# Inty GitHub issue labels

本仓库 **实际存在** 的 label（`gh label list`）。创建或 re-label issue 时 **只使用已有 label**；需要新 label 时先问 maintainer。

## 域（area）

| Label | 用途 |
|-------|------|
| `agentic_companion` | `/api/v1/chat/ws`、`companion_harness`、`living_sphere`、`techno_core` |
| `backend` | Ops HTTP API、非 companion 专属后端 |
| `android` | iMate / IntelliMate Android |
| `chat` | 聊天体验（UI + 后端 + 高级功能） |
| `UI` | 通用 UI |
| `运营` | 运营平台 |
| `cleanup` | 技术债、删除 dead code |
| `security` | 安全相关 |

## 类型

| Label | 用途 |
|-------|------|
| `enhancement` | 功能改进（GitHub 默认） |
| `feature` | 明确的新功能（常与 `enhancement` 同用） |
| `user-reported` | companion harness 自动上报的用户抱怨（`companion_record_user_feedback`） |
| `question` | 需要 reporter 补充信息 |
| `ui-nits` | 小 UI 修正 |
| `stainless` | 生成代码/SDK 相关 |

## 优先级 `p0`–`p3`

| Label | 含义 |
|-------|------|
| `p0` | 最高优先级（仅 maintainer 指定） |
| `p1` | 高 |
| `p2` | **默认** |
| `p3` | 低 |

每条 open issue 应有 **恰好一个** `p*` label。

## 严重程度 `s0`–`s3`（bug）

| Label | 含义 |
|-------|------|
| `s0` | 最严重 |
| `s1` | 重要 |
| `s2` | 一般 |
| `s3` | 轻微 |

Bug 类 issue 应有 **恰好一个** `s*` label；enhancement 可省略。

## Triage 状态（与 mattpocock `triage` skill 对齐）

若仓库尚未创建下列 label，创建 issue 时 **跳过** 并在 audit 报告里注明「缺 triage label」；不要自行 `gh label create` 除非 maintainer 同意。

| Canonical role | Label | 含义 |
|----------------|-------|------|
| `needs-triage` | `needs-triage` | 待评估 |
| `needs-info` | `needs-info` | 等 reporter |
| `ready-for-agent` | `ready-for-agent` | AFK agent 可接 |
| `ready-for-human` | `ready-for-human` | 需人类实现 |
| `wontfix` | `wontfix` | 不做 |

## 推荐组合

| 场景 | Labels |
|------|--------|
| Companion bug | `agentic_companion`, `s1`, `p2`, `needs-triage` |
| User-reported companion complaint | `user-reported`, `agentic_companion`, `s2`, `p2`, `needs-triage` |
| Companion feature | `agentic_companion`, `enhancement`, `feature`, `p2`, `needs-triage` |
| Backend bug | `backend`, `s2`, `p2`, `needs-triage` |
| Android feature | `android`, `enhancement`, `feature`, `p2`, `needs-triage` |
| Tech debt | `cleanup`, `backend` 或 `agentic_companion`, `p3` |
| Epic 母 issue | 域 label + `enhancement` + `p1` 或 `p2`；标题前缀 `[Epic]` |

## Issue 模板

创建时参考 [`.github/ISSUE_TEMPLATE/`](../../../.github/ISSUE_TEMPLATE/)：

- `agentic-companion-bug-report.md` → `[Agentic companion]` 标题 + `agentic_companion`
- `用户功能需求.md` → `android`, `enhancement`, `feature`, `p2`
- `后端系统-bug.md` → `backend` + severity
