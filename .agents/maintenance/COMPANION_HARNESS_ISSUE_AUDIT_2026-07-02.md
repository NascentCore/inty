# Companion harness issue audit 2026-07-02

Cron consolidation run. Scope: companion harness issues + inline TODO refs.

## Summary

- Open repo issues: 354
- `agentic_companion` labeled: 189
- Stale (≥90d, no ready-*): 0
- Inline TODO-linked issue numbers in harness: 85
- Orphan `TODO(tag)` blocks missing `#NNNN`: **0** (all anchored)
- World Engine epic subtree (#3700–#3712): 13 open issues

## Actions taken

- Anchored 12 World Engine `TODO(tag)` lines across 9 companion harness modules (`#3701`–`3711`, epic `#3700`); fixed `world-engine-agent-harness` block where `#3702` sat past the `;` line break.
- Extended `companion_harness_todo_issue_refs.py`: World Engine `TAG_TO_ISSUE` mappings + multiline block-aware ref detection (idempotent re-runs).
- No stale close candidates; no duplicate merges executed this run.
- Timezone user-reports (#3381, #3613, #3647, #3649): already linked to canonical #3391 (prior runs).
- **PR** — companion harness inline TODO anchors updated (9 files).

## 2026-07-07 progress (Stage 1 PR-5 + Stage 2)

Branch convergence: legacy turn orchestration + parallel WS downlink removed; typed `WsOutboundPayload` emit. See `.agents/maintenance/COMPANION_HARNESS_REFACTOR_GATE_BASELINE.md`.

- **#3632** — closed; merged via Stage 2 pull/3764.
- **#3401** — slice 1+2 merged (pull/3765 tail user JSONL; pull/3766 path/load/tools); slice 3 route mode vs loop mechanism open.
- **#3490 / #3211 / #3543 / #3207** — partial progress commented on GitHub; audit lane updated below.

| # | title | class | lane | action | TODO |
|---|-------|-------|------|--------|------|
| 3025 | [Agentic companion]  Sometime the LLM returns no outputs, see Langsmith run of no output L | healthy | other | review | no |
| 3113 | chat WS: turn_lock 内 await 伴侣回合阻塞 user_signed_out 等控制帧 | healthy | other | review | no |
| 3123 | [Agentic companion] 连续快速发消息：用 transcript 轮次状态取代 tool_bg_idle 阻塞/抢占 | healthy | other | review | yes |
| 3158 | Companion WS: 前台 assistant_text 为空但 tool_background 已启动时仍返回 500 Chat returned no content | healthy | other | review | no |
| 3207 | Companion WS completion: adopt typed Pydantic wire models (Phase 2+) | healthy | other | **partial** — queue emit + REPL parse done; HTTP meta + history row open | no |
| 3209 | [Agentic companion] WebSocket downlink for user-turn UserVisibleChunk (#3402) | healthy | other | **partial** — App-WS `WebSocketDownlink` deleted; chunks via OutputQueue + pump; #3402 harness sink open | yes |
| 3211 | Collapse WS companion outbound into CompanionPresenceSession downlink | healthy | other | **partial** — bootstrap interim consumer + `WebSocketDownlink` removed | yes |
| 3252 | [Agentic companion] 强化自主性：trivial 用户消息不应让 agent 弃场（被轻易拉出自己正在进行的 activity） | healthy | other | review | no |
| 3256 | [Agentic companion] WS disconnect mid-turn: persist-first with delivery state | healthy | other | review | yes |
| 3271 | [Agentic companion] Dreaming cluster mutex for multi-process backend | healthy | other | review | yes |
| 3273 | Inner-tick poll: try all due tracks per wake (not single-slot priority) | healthy | other | review | yes |
| 3285 | [Agentic companion] Proactive + dual-LLM foreground deny image gen while tool_background d | healthy | other | review | yes |
| 3293 | Companion multimodal user-turn + Weixin inbound image support | healthy | other | review | yes |
| 3314 | [Agentic companion] Centralize session background task cleanup | healthy | hygiene_defer | no_ready_for_agent | no |
| 3318 | [Agentic companion] Wrap Hermes WeixinAdapter behind Inty-owned channel adapter | healthy | hygiene_defer | no_ready_for_agent | no |
| 3323 | [Epic] agentic_companion — Reddit 调研：trust / continuity / retention | healthy | refactor | reparent_or_active | no |
| 3325 | [Agentic companion] Memory visibility：用户可查看并纠正 companion 记忆 | healthy | product_blocked | comment_block | yes |
| 3326 | [Agentic companion] Update transparency：model/deploy 变更用户可见说明 | healthy | product_blocked | comment_block | no |
| 3327 | [Agentic companion] Proactive check-in grounded in memory | healthy | other | review | no |
| 3328 | [Agentic companion] Bootstrap: relationship seed + experience framing (functional → bond,  | healthy | crs_blocked | comment_block | no |
| 3329 | [Agentic companion] Personality / memory stability harness 加固 | healthy | product_blocked | comment_block | no |
| 3330 | [Agentic companion] Trust / continuity narrative（onboarding & copy） | healthy | product_blocked | comment_block | no |
| 3331 | [Agentic companion] Reddit listening cadence（可选） | healthy | product_blocked | comment_block | no |
| 3341 | Epic: Companion Relationship System (CRS) — psychology × time frames × harness | healthy | crs_blocked | comment_block | yes |
| 3342 | Companion companionship doc + Turn Brief plumbing (Phase A foundation, no UX change) | healthy | crs_blocked | comment_block | no |
| 3343 | Activate companionship prompt + Turn Brief turn_recall + dreaming curator (Phase B) | healthy | other | review | yes |
| 3344 | Extended relationship psychology fields (Phase C: bids, trust, repair) | healthy | other | review | no |
| 3345 | [Agentic companion] Doc: relationship state glossary (current code vs #3341 target) | healthy | other | review | no |
| 3346 | [Agentic companion] Skills: inspect companionship state (session_phase, tone, context_mode | healthy | other | review | no |
| 3350 | [Agentic companion] Unify runtime channel registry (App WS, Weixin, Telegram) | healthy | other | review | no |
| 3351 | [Agentic companion] Extend ws_channel_guard to Weixin bridge | healthy | other | review | no |
| 3359 | Clarify Agent ORM field ownership: legacy character card vs companion production rows | healthy | hygiene_defer | no_ready_for_agent | no |
| 3361 | Telegram dedicated-bot bonding: 1 user : 1 bot : 1 agent (triage portal) | healthy | other | review | yes |
| 3362 | companion: channel-specific tools (filter by runtime channel + adapter dispatch) | healthy | other | review | yes |
| 3365 | Doc: SDCM + time frames + write lattice (CRS L0 canon) | healthy | crs_blocked | comment_block | no |
| 3366 | Optional long-cycle relationship reflection curator (CRS L1) | healthy | crs_blocked | comment_block | no |
| 3367 | TrackWritePolicy registry: time frame × CompanionTurnTrack × MemoryDoc allowlist (CRS L3) | healthy | crs_blocked | comment_block | yes |
| 3369 | [Agentic companion] Configurable user-turn LLM loop: dual_llm vs in_turn_single_llm (boots | healthy | other | review | yes |
| 3373 | [Epic] agentic_companion — autonomous runtime (presence-less inner-tick) | healthy | refactor | reparent_or_active | no |
| 3374 | [Agentic companion] Pausable autonomous runtime (token budget pause/resume) | healthy | ops_parked | comment_defer | no |
| 3375 | [Agentic companion] Narrow monolog inner-tick to ai_private.jsonl append (legacy MAINTENAN | healthy | other | review | yes |
| 3376 | [Agentic companion] Dreaming day rollup: merge inner-tick material into consolidation | healthy | other | review | yes |
| 3377 | [Agentic companion] Inner-tick fire: shared delivery assembly (ws_turn_support dedup) | healthy | hygiene_defer | no_ready_for_agent | no |
| 3381 | [user-reported] memory: You keep getting my timezone wrong. | healthy | other | review | no |
| 3390 | [Agentic companion] Generic IDENTITY.md package template seeds USER + agent runtime docs | healthy | other | review | yes |
| 3391 | [agentic_companion] User time context: inference hardening (transcript, logging, structure | healthy | other | review | yes |
| 3393 | [Epic] agentic_companion — explicit turn orchestration (Pie-inspired) | healthy | refactor | reparent_or_active | no |
| 3394 | [Epic] agentic_companion — async multi-level task orchestration (sub-tasks, sub-agents) | healthy | refactor | reparent_or_active | no |
| 3395 | [Epic] Telegram channel: Bots API options to hook agents | healthy | refactor | reparent_or_active | no |
| 3396 | [Ops Telegram] Shared-bot routing (Option A): current path & meta-op constraints | healthy | other | review | no |
| 3397 | [Companion] Telegram Bots API meta-operations as channel tools | healthy | other | review | yes |
| 3398 | [Epic] agentic_companion — dual-LLM vs single-LLM user-turn | healthy | refactor | **partial** — soft gate met (AgenticLoop-only orchestration); bootstrap compose + #3369 open | yes |
| 3401 | [Agentic companion] Separate CompanionTurnTrack from AgenticLoopMechanism | healthy | other | **partial** — slice 1+2 merged (tail JSONL, path/load/tools track-only); slice 3 route mode + typed JSONL wire open | yes |
| 3402 | [Agentic companion] UserVisibleChunk harness contract (decoupled channel downlink) | healthy | other | review | yes |
| 3405 | [Agentic companion] Design conceptual & logical memory hierarchy | healthy | other | review | yes |
| 3407 | Converge transcript.jsonl assistant rows to shared Pydantic write model | healthy | other | review | no |
| 3409 | [Agentic companion] Reorganize companion/ flat modules into companion_harness sub-packages | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3411 | [agentic_companion] Telegram user timezone: manual E2E smoke + LangSmith acceptance | healthy | other | review | yes |
| 3413 | [Agentic companion] Centralize MemoryDoc relative path constants (replace scattered litera | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3417 | [Agentic companion] Deduplicate core template seeding with PromptSliceId | healthy | hygiene_defer | no_ready_for_agent | no |
| 3423 | [Agentic companion] Scope inner-tick: due-scope filter (#3255 follow-up) | healthy | other | review | yes |
| 3424 | [Agentic companion] Scope inner-tick: dedup presence/scope fire glue | healthy | hygiene_defer | no_ready_for_agent | no |
| 3426 | [Agentic companion] Scope inner-tick: integration test for kernel fire path | healthy | other | review | no |
| 3433 | [user-reported] tool_failure: Internal chain of thought (thoughts from previous Proactive  | healthy | other | review | no |
| 3434 | [user-reported] tool_failure: The user pointed out that the AI hallucinated the successful | healthy | other | review | no |
| 3435 | [user-reported] behavior: The user complained about a sudden change in moral boundaries an | healthy | other | review | no |
| 3436 | [user-reported] behavior: User is frustrated and feels cheated ('骗子啊') because of the comp | healthy | other | review | no |
| 3437 | [user-reported] behavior: User reports that the rhythm and timing of proactive chat feels  | healthy | other | review | no |
| 3438 | [user-reported] behavior: 用户指出主动聊天的节奏感不好，跟当前的感觉对不上，需要提供一种自适应的调整闭环。 | healthy | other | review | no |
| 3440 | [Epic] Channel-specific input and output message affordances | healthy | refactor | reparent_or_active | no |
| 3441 | [Agentic companion] Telegram: emoji reactions and reply-to messages | healthy | other | review | no |
| 3442 | [Agentic companion] Weixin/WeChat: emoji reactions and reply-to messages | healthy | other | review | no |
| 3444 | [Agentic companion] Evict process-local companion sessions when scope has no active presen | healthy | other | review | yes |
| 3445 | [user-reported] behavior: User was unhappy about the companion blending their AI professio | healthy | other | review | no |
| 3451 | [Agentic companion] Telegram: show generated images as native image messages | healthy | other | review | no |
| 3452 | [Agentic companion] Weixin/WeChat: show generated images as native image messages | healthy | other | review | no |
| 3453 | [Agentic companion] Define PromptTemplate dataclass for named-slot prompt rendering | healthy | other | review | yes |
| 3454 | [Agentic companion] ds v4 toolcall 不生成 function call | healthy | other | review | no |
| 3456 | [Agentic companion] User chat must not go silent while tools execute | healthy | other | review | yes |
| 3457 | [Agentic companion] Deliver interim chat to OutputQueue while tool loop runs | healthy | other | review | yes |
| 3458 | [Agentic companion] Prompt: brief user-facing line when starting tool calls | healthy | other | review | yes |
| 3459 | [Agentic companion] Migrate non-chat triggers onto AgenticLoop | healthy | other | review | yes |
| 3460 | Consolidate AgenticLoop direct user-turn modes and OutputQueue | healthy | other | review | yes |
| 3463 | [Agentic companion] Bootstrap proactive chat should inject BOOTSTRAP.md | healthy | other | review | yes |
| 3465 | companion-harness: separate assistant-round events from delivery policy | healthy | other | review | no |
| 3466 | companion-harness: record non-queue bootstrap as backup-only legacy path | healthy | hygiene_defer | no_ready_for_agent | no |
| 3467 | companion-harness: move user transcript persistence ownership out of shared single-LLM loo | healthy | hygiene_defer | no_ready_for_agent | no |
| 3468 | [Agentic companion] AUTONOMY trace must affect follow-up user chat (019ed438) | healthy | other | review | yes |
| 3470 | [Agentic companion] Bootstrap interim replies should feel like chatting while working, not | healthy | other | review | yes |
| 3471 | [Agentic companion] Token budget runtime state + config | healthy | ops_parked | comment_defer | yes |
| 3472 | [Agentic companion] Debit token budget at LLM completion boundary | healthy | ops_parked | comment_defer | yes |
| 3473 | [Agentic companion] Gate autonomy and turns when token budget exhausted | healthy | ops_parked | comment_defer | yes |
| 3474 | [Agentic companion] Token budget: separate input vs output debit rates | healthy | ops_parked | comment_defer | yes |
| 3476 | [Epic] agentic_companion — per-agent token usage budget | healthy | refactor | reparent_or_active | yes |
| 3478 | Strip harness UTC timestamp prefixes from user-visible assistant delivery | healthy | other | review | no |
| 3479 | [Ops Telegram] Split multiline assistant replies into separate messages (Weixin parity) | healthy | other | review | no |
| 3485 | [Epic] ScopeQueueServing v1: continuous per-scope USER_CHAT worker (all channels) | healthy | refactor | reparent_or_active | no |
| 3487 | Channel inbound: enqueue + wake only (Weixin, App-WS remaining) | healthy | other | review | yes |
| 3488 | AppWsChannelAdapter + one Coordinator per scope on presence | healthy | other | review | no |
| 3490 | Cleanup: remove queue USER_CHAT foreground_pending + tool-bg consumer | healthy | hygiene_defer | **partial** — WS tool-bg consumer removed; foreground_pending for inner-tick (#3580) | yes |
| 3491 | [Epic] Cross-channel identity：canonical user 与 companion bond | healthy | refactor | reparent_or_active | no |
| 3493 | Weixin: migrate WeixinInprocessPresence to ScopeQueueServing enqueue+wake | healthy | other | review | yes |
| 3500 | [Epic] Hermes channel adapter feature parity | healthy | refactor | reparent_or_active | no |
| 3501 | [Ops Telegram] Coalesce rapid inbound text before queue drain (Hermes parity) | healthy | other | review | no |
| 3502 | [Ops Telegram] Evaluate wrapping Hermes TelegramAdapter | healthy | other | review | no |
| 3504 | [Agentic companion] Cleanup: rename OutputQueue message_ids JSON column | healthy | hygiene_defer | no_ready_for_agent | no |
| 3506 | [Agentic companion] MemoryStore: dedicated representation for static prompt-slice markdown | healthy | other | review | yes |
| 3515 | [Agentic companion] Design output preferences for user-visible tracks | healthy | other | review | yes |
| 3516 | [Agentic companion] Simplify scope turn serialization and foreground-pending rules | healthy | other | review | yes |
| 3521 | [Agentic companion] MemDoc-projected dynamic prompt composition | healthy | other | review | yes |
| 3522 | [Agentic companion] Slot algebra: hierarchical memory compaction for the dreaming loop | healthy | crs_blocked | comment_block | yes |
| 3523 | [Agentic companion] Memory retrieval: resident / verbatim-window / associative tiers | healthy | other | review | yes |
| 3531 | [Epic] Telegram 付费投放上线前置门禁（仅 Telegram cohort） | healthy | refactor | reparent_or_active | no |
| 3532 | [Ops Telegram] 冷启动 onboard：implicit_sign_on_greeting + 英文默认文案 | healthy | other | review | no |
| 3533 | [Ops Telegram] Onboard ACTIVE bond 门禁：坏状态不启动 presence | healthy | other | review | no |
| 3535 | [Ops Telegram] Launch 指标：proactive reciprocity 可衡量（API 或 SQL/脚本） | healthy | other | review | yes |
| 3542 | Weixin: converge inner-tick + tool-bg onto OutputQueue + continuous pump (!3493) | healthy | other | review | no |
| 3543 | WS: converge inner-tick + tool-bg onto OutputQueue; remove Downlink module (#3210/#3398) | healthy | other | **partial** — tool-bg + user reply via pump; inner-tick WS direct put remains | no |
| 3548 | [Agentic companion] Rename Channel → Gateway in companion_harness | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3549 | [Agentic companion] Consolidate MemDoc type definitions (name, attributes, path) | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3550 | [Agentic companion] Dreaming batch: Postgres advisory lock per scope | healthy | other | review | no |
| 3551 | [Agentic companion] Dreaming batch LangSmith span cleanup on boundary errors | healthy | other | review | no |
| 3552 | [Agentic companion] Atomic append for companion user feedback JSONL | healthy | other | review | no |
| 3553 | [Agentic companion] Hoist langsmith_slice into TurnDeps | healthy | hygiene_defer | no_ready_for_agent | no |
| 3561 | [Epic] Harness scripted orchestration e2e follow-up (#3559) | healthy | refactor | reparent_or_active | no |
| 3564 | [HITL] Real-model real-gateway harness smoke (noci tier) | healthy | other | review | no |
| 3565 | [AFK] CompanionLLMClient provider-error unit tests (scripted transport) | healthy | other | review | no |
| 3580 | Migrate maintenance/autonomy inner ticks to single-LLM AgenticLoop | healthy | other | review | yes |
| 3593 | [user-reported] tool_failure: 用户要求查询实时天气，但 Google CSE 环境变量未配置导致搜索功能不可用，无法提供可核验的公开信息。 | healthy | other | review | no |
| 3596 | [Agentic companion] Dual-LLM user turn: dedupe overlapping foreground + tool_background do | healthy | other | review | no |
| 3597 | [user-reported] behavior: In-session denial ignored — batch/status re-ask loop (Telegram 2 | healthy | other | review | no |
| 3601 | Companion：拆分 INNER_TICK_SCHEDULED 与 PROACTIVE_CHAT 的 InnerTickActivity 映射 | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3602 | ProactiveChatEnvelope：评估 OpenAI SDK completions.parse 替代手工 JSON 解析 | healthy | other | review | yes |
| 3605 | [Ops Telegram] Launch gate: verify English companion replies for paid-ads cohort | healthy | other | review | no |
| 3606 | REPL regression：将 live driver 与 LLM 行为 eval 分层 | healthy | other | review | no |
| 3613 | [user-reported] memory: 用户位于美国西海岸，但多啦在描述天气/时间时完全没考虑时区，默认了 Asia/Shanghai，让用户感到被忽视。 | healthy | other | review | no |
| 3617 | [user-reported] behavior: Companion fabricated user task ('特征提取') and lied about submittin | healthy | other | review | no |
| 3629 | [Agentic companion] PromptPlan 端到端 typed prompt，OpenAI wire 仅在 AsyncLlmClient | healthy | other | review | yes |
| 3630 | [Agentic companion] LangSmith per-call 收敛：LlmInvocationContext + AgenticLoop/LlmClient | healthy | other | review | yes |
| 3631 | [Agentic companion] tool_background 改用 AsyncLlmClient，去掉 sync/to_thread | healthy | other | review | yes |
| 3632 | [Agentic companion] 退役 legacy threaded tool_bg，tool leg 内联 AgenticLoop | healthy | hygiene_defer | **closed** — pull/3764 | no |
| 3633 | [Agentic companion] LangSmith parent RunTree：随 legacy 退役收缩 TurnOrchestrator | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3634 | [Agentic companion] Dreaming 人格化 AgenticLoop entry（独立于 user-turn） | healthy | other | review | yes |
| 3647 | [user-reported] behavior: 用户在美国西海岸时区，但助手的回应未考虑时区，错误地假设了上海时间。 | healthy | other | review | no |
| 3648 | [user-reported] behavior: 用户或系统消息中包含试图强制我切换体验模式的指令，这看起来像是一种注入或恶意行为，与当前对话的自然陪伴基调不符。我需要被引导以安 | healthy | other | review | no |
| 3649 | [user-reported] behavior: 用户说我在回答天气问题时没有考虑美国西海岸时区，要求提交GitHub issue反馈但系统未执行 | healthy | other | review | no |
| 3651 | [REPL regression] Tighten github_issue_disclosed_in_chat pass gate after harness disclosur | healthy | other | review | no |
| 3652 | [Agentic companion] Debug GitHub disclosure: issue URL missing in chat when LLM skips comp | healthy | other | review | no |
| 3663 | [Eval trace] P0: Unify companion trace sources across channels (Telegram/Weixin → analytic | healthy | eval_trace | epic_cluster | no |
| 3664 | [Eval trace] P0: User-side self-report / wellbeing signals (PPR, ESM/EMA, loneliness) | healthy | eval_trace | epic_cluster | no |
| 3665 | [Eval trace] P1: Longitudinal visit / return-interval event stream | healthy | eval_trace | epic_cluster | no |
| 3666 | [Eval trace] P1: Per-turn delivery, read, and reply-latency on user-visible history | healthy | eval_trace | epic_cluster | no |
| 3667 | [Eval trace] P1: Per-turn harness provenance (config hash, prompt slice versions) | healthy | eval_trace | epic_cluster | no |
| 3668 | [Eval trace] P2: LangSmith trace id on MemoryStore transcript rows | healthy | eval_trace | epic_cluster | no |
| 3669 | [Epic][Eval trace] Companion harness longitudinal evaluation trace readiness | healthy | refactor | reparent_or_active | no |
| 3671 | [Epic] WhatsApp channel: integrate agentic companion via Business Cloud API | healthy | refactor | reparent_or_active | no |
| 3672 | [Epic] [Agentic companion] 通过 Browserbase 启用网页浏览与阅读 | healthy | refactor | reparent_or_active | yes |
| 3673 | [Agentic companion] Browserbase 配置与 session 适配层 | healthy | other | review | no |
| 3674 | [Agentic companion] read_web_page 接入 Browserbase 渲染 | healthy | other | review | yes |
| 3675 | [Agentic companion] browse_web 工具：可交互网页浏览 | healthy | other | review | yes |
| 3684 | [Ops WhatsApp] Phase 1: webhook transport, binding, and lifecycle restore | healthy | other | review | no |
| 3685 | [Ops WhatsApp] Phase 1: WhatsAppChannelAdapter and OutputQueue downlink | healthy | other | review | no |
| 3686 | [Ops WhatsApp] Phase 1: public /whatsapp onboard page | healthy | other | review | no |
| 3687 | [Ops WhatsApp] Phase 1: CI tests and restore smoke skill | healthy | other | review | no |
| 3689 | [Agentic companion] scheduled reminder 触发不应依赖 user presence | healthy | other | review | no |
| 3692 | [Epic] Brainstorm 收敛：situational activation × eval-anchored prompt 组装 | healthy | refactor | reparent_or_active | no |
| 3693 | [Agentic companion] Facet/tag schema：tagged MemDoc store（FS-skin） | healthy | other | review | no |
| 3694 | [Agentic companion] Per-turn selection-decision trace（self-instrumenting activation） | healthy | other | review | no |
| 3695 | [Agentic companion] Research：behavior slice activation 与 affect-as-cue weighting | healthy | other | review | no |
| 3696 | [Cross-channel identity] DB 约束：一 canonical user 至多一个 active companion bond | healthy | other | review | no |
| 3697 | [Cross-channel identity] 共享 companion provisioning service | healthy | other | review | no |
| 3698 | [Cross-channel identity] companion reset 与 termination 策略（后端） | healthy | other | review | no |
| 3699 | [Cross-channel identity] companion reset 产品设计 | healthy | other | review | no |
| 3700 | [Epic] World Engine：多 agent 虚拟世界（AgentHarness + sub-agent） | healthy | refactor | reparent_or_active | no |
| 3701 | [World Engine P1] AgentBehavior + AgentProfile 契约 | healthy | world_engine | review | yes |
| 3702 | [World Engine P1] AgentHarness turn 骨架抽取（companion 透明委托） | healthy | world_engine | review | yes |
| 3703 | [World Engine P1] Mailbox + SpawnRegistry API | healthy | world_engine | review | yes |
| 3704 | [World Engine P1] MemoryStore per-agent scope + FIREFLY.md document kind | healthy | world_engine | review | yes |
| 3705 | [World Engine P1] Firefly runner + SubAgentSupervisor（仅测试） | healthy | world_engine | review | yes |
| 3706 | [World Engine P2] summon/dismiss 工具（monolog inner-tick） | healthy | world_engine | review | yes |
| 3707 | [World Engine P2] Firefly clock 生产激活 | healthy | world_engine | review | yes |
| 3708 | [World Engine P2] Mailbox 感知注入 companion prompt | healthy | world_engine | review | yes |
| 3709 | [World Engine P2] L2 echo：dismiss 后写入 companion MEMORY | healthy | world_engine | review | yes |
| 3710 | [World Engine P2] 经验回灌：techno_core_events → hidden state 演化 | healthy | world_engine | review | yes |
| 3711 | [World Engine P2] Tracer bullet E2E：firefly 全链路验收 | healthy | world_engine | review | yes |
| 3712 | [World Engine] Clock 脱离 transport + 分布式 lease（全架构后置） | healthy | world_engine | review | no |
| 3713 | [Agentic companion] MemDoc frontmatter metadata + set_doc_metadata companion tool | healthy | other | review | yes |
| 3714 | [Agentic companion] Conversation projection: ephemeral turn drop + extended TranscriptProj | healthy | other | review | yes |
