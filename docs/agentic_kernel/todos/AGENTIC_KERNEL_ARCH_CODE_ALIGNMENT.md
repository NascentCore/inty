# Agentic kernel 架构代码对齐 TODO

本文记录 `docs/agentic_kernel/ARCH.md` 指定架构后的代码跟进清单：生产 companion turn 以 `CompanionManager` / `CompanionSession` + `run_turn` + `CompanionTurnResult` 为语义真源，WebSocket 与实验 orchestrator 只能作为 adapter。

## P0：固定生产 turn 合同

- [ ] 定义 companion 专用 turn input / context Pydantic 模型，字段至少覆盖 scope、`MemoryStore` 绑定引用、implicit signal、inner tick mode、background output sink、preset `user_msg_uuid`、memory bootstrap type 与 transcript 配置。
- [ ] 让 `CompanionManager.run_turn` 接收该合同或在内部立即构造该合同，减少 `run_turn` 的长参数列表。
- [ ] 保持 `CompanionTurnResult` 为用户可见输出与审计 metadata 的生产返回真源；不要用 `contracts/turn.py::TurnOutput` 替换它。

## P0：收敛并行 turn 抽象

- [ ] 将 `runtime/TurnOrchestrator` 明确限制为实验 adapter；若未来复用名称，先扩展 companion 专用合同，再让 orchestrator 包装 `CompanionManager.run_turn`。
- [ ] 审查 `companion/turn_engine.py` 的 REPL helper：生产重复逻辑必须改为调用 `CompanionManager.run_turn` 或迁入 `turn_pipeline.py` 的共享阶段合同。
- [ ] 删除或降级任何绕过 `run_turn` 直接拼 prompt、写 transcript、启动 tool background 的新入口。

## P0：补齐事件一致性测试

- [ ] 为“前台 assistant 已返回、tool_background 随后成功补帧”增加契约测试：断言 transcript、chat_history metadata、WS background frame 使用同一 `user_msg_uuid` / `trace_id`。
- [ ] 为“tool_background 超时或失败”增加契约测试：断言 runtime event 可追踪，下一轮不会把失败伪装为成功工具结果。
- [ ] 为“用户下一条消息早于上一轮 tool_background 完成”增加测试或 smoke：断言 `tool_bg_idle` wait 超时路径有 warning 和 trace，不承诺严格全序。

## P1：瘦身 API 与服务边界

- [ ] 将 `companion_chat_service._maybe_append_companion_ws_session_system` 下沉为 session bootstrap 能力，由 companion session facade 统一写 MemoryStore transcript 与需要镜像的外部事件。
- [ ] 把 `chat.py` 中 proactive heartbeat / maintenance inner tick 的 worker 逻辑抽到 companion WebSocket handler 模块；endpoint 保留路由、依赖注入和 transport framing。
- [ ] 把 tool_bg drain 到 chat_history / WS frame 的逻辑抽成明确的 transport adapter，输入只接受内核 background event。

## P1：MemoryStore scope 演进

- [ ] 在不破坏现有 `CompanionScope(user_id, companion_id, chat_id)` registry 的前提下，设计 user-scoped / companion-scoped corpus 的读取顺序与投影任务。
- [ ] 将长期关系记忆从 chat-scoped transcript 中提炼到上层 corpus 的策略写成可测试合同，避免 `MEMORY.md` 独自承担跨会话关系记忆。
- [ ] 为 future LTM 注入点增加基线测试：同一 turn prompt 中 MemoryStore 文档记忆与向量 LTM 只出现一次，且顺序稳定。

## P2：命名与文档清理

- [ ] 将 `workspace` 口语逐步替换为 `SessionBinding` / `SessionCorpus` / sidecar 分类；迁移计划见 `AGENTIC_KERNEL_ARCH_ENHANCEMENT.md`。
- [ ] 更新相关 `AGENTS.md`：标注 `TurnOrchestrator` 非生产 companion 真源，标注 `turn_engine.py` 为 REPL-grade helper。
- [ ] 代码改动完成后回修 `ARCH.md` 的“当前偏差”列，避免文档长期停留在过渡态。
