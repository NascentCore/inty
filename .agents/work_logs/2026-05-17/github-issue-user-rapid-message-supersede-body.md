## 问题类型

**产品行为缺口**（非 inner-tick / `tool_bg_idle` 队头阻塞类 bug）。与 [#3105](https://github.com/NascentCore/inty/pull/3105) 调查的 **`turn_lock` + maintenance / 僵死 `tool_background` 队头阻塞** 相关但子类不同；勿与 [#3102](https://github.com/NascentCore/inty/pull/3102) 讨论的 **outbound 队列 head-of-line** 混为一谈。

仓库内调查笔记：`.agents/work_logs/2026-05-17/companion-ws-turn-lock-head-of-line-blocking-analysis.md`（HoL 现状）；本 issue 追踪 **用户 vs 用户连发抢占**。

## 期望行为（真人「打断」）

当用户在上一轮 **user-turn 尚未结束** 时快速再发一条（及后续连发）：

1. **新消息取消整轮旧 user-turn**（不仅是排队等待旧回合跑完）。
2. 通过 **streaming** 捕获旧回合已产生的 **partial assistant 输出**。
3. 回复 **最新一条** 用户消息时，transcript / 模型上下文应 **只纳入** 旧回合的 partial 结果（以及已确定的 user 侧内容），使回复更像真人被打断后的接续，而不是对每条消息各给一条完整独立回复。
4. **连续生效**：若第 3 条在回复第 2 条完成前到达，则同样取消对第 2 条的回复，仅保留其 partial stream，以此类推。

## 当前行为

- `/api/v1/chat/ws` 伴侣路径：收包主循环在 `companion_ws.turn_lock` 内 **`await` 整轮** `_agent_chat_completions_impl` 结束后才处理下一条用户 chat → **第二条消息排队**，不取消第一条。
- 伴侣 HTTP/WS 路径标明 **不支持 stream**（`Stream is not supported`），尚无「流式截断 → 并入下一轮」机制。
- `mark_tool_background_aborted` / `BackgroundToolLoopAborted` 仅面向 **REPL 抢占后台 tool**，生产 WS **未**在「新用户消息」时 wired。

## 与已有跟进项的边界

| 项 | 关系 |
|----|------|
| PR #3105 正文提到的 #3113「读循环与 chat turn 解耦」 | 可能 **必要前置**（否则无法在持锁 await 整轮时收下一条），但 **不等价** 于本需求的 cancel + partial |
| PR #3105 队头阻塞（用户被 inner-tick / `tool_bg` 拖住） | **不同根因**；本 issue 是 **同连接上用户连发互相抢占** |
| 历史 #1687「抢话」 | 概念相近，需产品确认是否同一能力在 companion WS 的落地 |

## 建议实现方向（供讨论）

- **抢占语义**：新 `user_msg_uuid` 到达 → cancel 当前 inflight user-turn task；`tool_background` 对旧 uuid 走 abort（可复用/扩展 `mark_tool_background_aborted`）。
- **Partial 捕获**：前台 LLM 改为可取消的 stream；取消时 flush 已生成 token/结构化片段 → 以约定 transcript 形态写入（需定义：是否对用户可见、是否落库、meta_data 标记 `superseded` / `partial`）。
- **读循环**：与 #3113 类「解耦」一并设计，避免仍被 `turn_lock` + 整轮 await 挡住收包。
- **测试**：REPL 或 WS 集成测——连发两条/三条，断言仅 **一条** 最终完整回复、旧回合 partial 出现在最新轮的上下文中。

## 验收标准（草案）

- [ ] 连发 2 条用户消息：第一条 turn 被取消，第二条回复引用第一条的 partial（非两条完整 assistant 消息）。
- [ ] 第三条在第二条完成前到达：第二条 turn 同样被取消，仅保留 partial，最终只完成第三条对应回复。
- [ ] 与 maintenance inner-tick 占锁导致的 HoL（#3105）回归隔离：本改动不恶化「用户消息被 tool_bg 拖住数分钟」场景（或另 issue 处理）。

## 环境

- 端点：伴侣 `POST /api/v1/chat/ws`（`chat_route=websocket`）
- 复现：本地 `inty_v2_repl` 或 iMate；快速连续发送两条以上 user chat 帧
