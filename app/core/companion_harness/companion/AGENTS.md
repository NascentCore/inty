# `companion` 子包：单轮编排与记忆真源

**一句话**：这里把 **一轮对话** 从「读记忆 → 拼系统消息 → 调模型 → 异步工具 → 写回记忆/流水」串成 **可预测的管道**；**角色与伴侣状态以记忆文档与版本表为准**，而不是去读传统「角色卡 ORM」当推理真源。

## 读者

- 需要改 **回合路由、提示词栈、同步 LLM 端口、后台工具、显著性（significance）** 或 **transcript 语义** 的维护者。

## 概念要点

- **编排主轴**：单轮内顺序大致为——加载 MemoryStore 文档 → 组装多段 system → 前台对话 → 视配置启动异步工具 → 处理显著性信封 → 更新 transcript / 运行时事件。
- **记忆真源**：持久化正文与版本在 Postgres 的伴侣记忆版本表中；推理只信任这条链路上的文档；网关仍可用传统 agent 表做 **存在性** 等检查，但 **不把 ORM 当 prompt 真源**。
- **记忆种类（直觉）**：从「当天情景片段」「一日摘要」到「长期语义记忆」分桶；全局约束在 system 中越靠前越强；模板与固定教义分流在 `templates/` 与 `prompts/` 两类来源。
- **体验状态 `context.json`**：记录当前体验档位、引导是否完成等；**应由工具与会话流程改写**，而不是随手当普通 Markdown 文档写入。
- **异步工具与双轨回复**：用户轮可能先返回「不含工具的薄回复」，再在后台跑工具并追加结果；维护性 inner tick 可走更短路径；前后台工具策略以 **契约与提示词栈** 为准，细节见 `docs/companion_harness/MEMORY_STORE.md` 与源码。

## 活跃轨道（入口 API）

同一 ``CompanionScope`` / ``MemoryStore`` 上，WebSocket 与调度器通过 **五条显式轨道** 进入内核，不再在边界传 ``inner_tick_turn`` / ``inner_tick_mode`` 组合：

| 轨道 | Service / Manager | 内核 |
|------|-------------------|------|
| 用户聊天 | ``run_companion_user_chat_turn_for_api`` | ``CompanionTurnTrack.USER_CHAT`` |
| 隐式上线问候 | ``run_companion_implicit_sign_on_greeting_turn_for_api`` | ``IMPLICIT_SIGN_ON_GREETING`` |
| 陪伴主动聊天 | ``run_companion_inner_tick_proactive_chat_turn_for_api`` | ``INNER_TICK_PROACTIVE_CHAT`` |
| 定时提醒 inner tick | ``run_companion_inner_tick_scheduled_turn_for_api`` | ``INNER_TICK_SCHEDULED`` |
| 维护 inner tick | ``run_companion_inner_tick_maintenance_turn_for_api`` | ``INNER_TICK_MAINTENANCE`` |

``INNER_TICK_SCHEDULED`` 将 ``schedule_queue`` 合成用户行原样进 LLM/transcript（``scheduled: true``，无 ``proactive_chat``）；工具面与 proactive 同轨（``InnerTickActivity.PROACTIVE_CHAT``）。

``turn_lock``（每 WebSocket 连接）与 ``tool_bg_idle``（每 session）串行化各轨道；``tool_background`` 线程是用户轮与维护 tick 上的第三条执行流。TechnoCore 事件轨道尚未实现。

## 深入阅读

- 表结构、registry 键、路径与 `document_kind` 映射等 **机械细节**：[`/docs/companion_harness/MEMORY_STORE.md`](/docs/companion_harness/MEMORY_STORE.md)。
