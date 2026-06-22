# Companion harness issue audit 2026-06-22

Phase -1 baseline. Maintainer approved via plan execution.

| # | title | class | lane | action | TODO |
|---|-------|-------|------|--------|------|
| 3025 | [Agentic companion]  Sometime the LLM returns no outputs, se | healthy | other | review | no |
| 3113 | chat WS: turn_lock 内 await 伴侣回合阻塞 user_signed_out 等控制帧 | healthy | refactor | reparent_or_active | no |
| 3123 | [Agentic companion] 连续快速发消息：用 transcript 轮次状态取代 tool_bg_idle | healthy | refactor | reparent_or_active | yes |
| 3158 | Companion WS: 前台 assistant_text 为空但 tool_background 已启动时仍返回  | healthy | other | review | no |
| 3162 | [Epic][Agentic companion] WS 连接被占满：user-input 无 chat + 控制帧排队 | duplicate | refactor | close | no |
| 3207 | Companion WS completion: adopt typed Pydantic wire models (P | healthy | other | review | no |
| 3209 | [Agentic companion] WebSocket downlink for user-turn UserVis | healthy | other | review | yes |
| 3211 | Collapse WS companion outbound into CompanionPresenceSession | healthy | other | review | yes |
| 3252 | [Agentic companion] 强化自主性：trivial 用户消息不应让 agent 弃场（被轻易拉出自己正在 | healthy | other | review | no |
| 3256 | [Agentic companion] WS disconnect mid-turn: persist-first wi | healthy | other | review | yes |
| 3271 | [Agentic companion] Dreaming cluster mutex for multi-process | healthy | refactor | reparent_or_active | yes |
| 3273 | Inner-tick poll: try all due tracks per wake (not single-slo | healthy | refactor | reparent_or_active | yes |
| 3285 | [Agentic companion] Proactive + dual-LLM foreground deny ima | healthy | other | review | yes |
| 3293 | Companion multimodal user-turn + Weixin inbound image suppor | healthy | refactor | comment_defer | yes |
| 3295 | Consolidate companion multimodal wire adapters and channel g | duplicate | refactor | close_merge_parent | no |
| 3296 | CompanionUserTurnInput boundary at run_user_chat; multimodal | duplicate | refactor | close_merge_parent | no |
| 3314 | [Agentic companion] Centralize session background task clean | healthy | hygiene_defer | no_ready_for_agent | no |
| 3318 | [Agentic companion] Wrap Hermes WeixinAdapter behind Inty-ow | healthy | other | review | no |
| 3323 | [Epic] agentic_companion — Reddit 调研：trust / continuity / re | healthy | product_blocked | comment_block | no |
| 3325 | [Agentic companion] Memory visibility：用户可查看并纠正 companion 记忆 | healthy | product_blocked | comment_block | yes |
| 3326 | [Agentic companion] Update transparency：model/deploy 变更用户可见说 | healthy | product_blocked | comment_block | no |
| 3327 | [Agentic companion] Proactive check-in grounded in memory | healthy | product_blocked | comment_block | no |
| 3328 | [Agentic companion] Bootstrap: relationship seed + experienc | healthy | product_blocked | comment_block | no |
| 3329 | [Agentic companion] Personality / memory stability harness 加 | healthy | product_blocked | comment_block | no |
| 3330 | [Agentic companion] Trust / continuity narrative（onboarding  | healthy | product_blocked | comment_block | no |
| 3331 | [Agentic companion] Reddit listening cadence（可选） | healthy | product_blocked | comment_block | no |
| 3341 | Epic: Companion Relationship System (CRS) — psychology × tim | healthy | crs_blocked | comment_block | yes |
| 3342 | Companion companionship doc + Turn Brief plumbing (Phase A f | healthy | crs_blocked | comment_block | no |
| 3343 | Activate companionship prompt + Turn Brief turn_recall + dre | healthy | crs_blocked | comment_block | yes |
| 3344 | Extended relationship psychology fields (Phase C: bids, trus | healthy | crs_blocked | comment_block | no |
| 3345 | [Agentic companion] Doc: relationship state glossary (curren | healthy | crs_blocked | comment_block | no |
| 3346 | [Agentic companion] Skills: inspect companionship state (ses | healthy | crs_blocked | comment_block | no |
| 3350 | [Agentic companion] Unify runtime channel registry (App WS,  | healthy | other | review | no |
| 3351 | [Agentic companion] Extend ws_channel_guard to Weixin bridge | healthy | other | review | no |
| 3359 | Clarify Agent ORM field ownership: legacy character card vs  | healthy | other | review | no |
| 3361 | Telegram dedicated-bot bonding: 1 user : 1 bot : 1 agent (tr | healthy | other | review | yes |
| 3362 | companion: channel-specific tools (filter by runtime channel | healthy | other | review | yes |
| 3365 | Doc: SDCM + time frames + write lattice (CRS L0 canon) | healthy | crs_blocked | comment_block | no |
| 3366 | Optional long-cycle relationship reflection curator (CRS L1) | healthy | crs_blocked | comment_block | no |
| 3367 | TrackWritePolicy registry: time frame × CompanionTurnTrack × | healthy | crs_blocked | comment_block | yes |
| 3369 | [Agentic companion] Configurable user-turn LLM loop: dual_ll | healthy | refactor | reparent_or_active | yes |
| 3373 | [Epic] agentic_companion — autonomous runtime (presence-less | healthy | refactor | reparent_or_active | no |
| 3374 | [Agentic companion] Pausable autonomous runtime (token budge | healthy | other | review | no |
| 3375 | [Agentic companion] Narrow monolog inner-tick to ai_private. | healthy | refactor | reparent_or_active | yes |
| 3376 | [Agentic companion] Dreaming day rollup: merge inner-tick ma | healthy | other | review | yes |
| 3377 | [Agentic companion] Inner-tick fire: shared delivery assembl | healthy | refactor | reparent_or_active | no |
| 3381 | [user-reported] memory: You keep getting my timezone wrong. | healthy | other | review | no |
| 3390 | [Agentic companion] Generic IDENTITY.md package template see | healthy | other | review | yes |
| 3391 | [agentic_companion] User time context: inference hardening ( | healthy | other | review | yes |
| 3393 | [Epic] agentic_companion — explicit turn orchestration (Pie- | overlap | refactor | comment_superseded | no |
| 3394 | [Epic] agentic_companion — async multi-level task orchestrat | overlap | refactor | comment_superseded | no |
| 3395 | [Epic] Telegram channel: Bots API options to hook agents | healthy | other | review | no |
| 3396 | [Ops Telegram] Shared-bot routing (Option A): current path & | healthy | other | review | no |
| 3397 | [Companion] Telegram Bots API meta-operations as channel too | healthy | other | review | yes |
| 3398 | [Epic] agentic_companion — dual-LLM vs single-LLM user-turn | healthy | refactor | reparent_or_active | yes |
| 3400 | [Agentic companion] Rename INNER_TICK_MAINTENANCE to INNER_T | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3401 | [Agentic companion] Separate CompanionTurnTrack from Agentic | healthy | refactor | reparent_or_active | yes |
| 3402 | [Agentic companion] UserVisibleChunk harness contract (decou | healthy | refactor | reparent_or_active | yes |
| 3405 | [Agentic companion] Design conceptual & logical memory hiera | healthy | other | review | yes |
| 3407 | Converge transcript.jsonl assistant rows to shared Pydantic  | healthy | hygiene_defer | no_ready_for_agent | no |
| 3409 | [Agentic companion] Reorganize companion/ flat modules into  | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3411 | [agentic_companion] Telegram user timezone: manual E2E smoke | healthy | other | review | yes |
| 3413 | [Agentic companion] Centralize MemoryDoc relative path const | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3417 | [Agentic companion] Deduplicate core template seeding with P | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3423 | [Agentic companion] Scope inner-tick: due-scope filter (#325 | healthy | other | review | yes |
| 3424 | [Agentic companion] Scope inner-tick: dedup presence/scope f | healthy | other | review | no |
| 3426 | [Agentic companion] Scope inner-tick: integration test for k | healthy | other | review | no |
| 3433 | [user-reported] tool_failure: Internal chain of thought (tho | healthy | other | review | no |
| 3434 | [user-reported] tool_failure: The user pointed out that the  | healthy | other | review | no |
| 3435 | [user-reported] behavior: The user complained about a sudden | healthy | other | review | no |
| 3436 | [user-reported] behavior: User is frustrated and feels cheat | healthy | other | review | no |
| 3437 | [user-reported] behavior: User reports that the rhythm and t | healthy | other | review | no |
| 3438 | [user-reported] behavior: 用户指出主动聊天的节奏感不好，跟当前的感觉对不上，需要提供一种自适应 | healthy | other | review | no |
| 3440 | [Epic] Channel-specific input and output message affordances | healthy | other | review | no |
| 3441 | [Agentic companion] Telegram: emoji reactions and reply-to m | healthy | other | review | no |
| 3442 | [Agentic companion] Weixin/WeChat: emoji reactions and reply | healthy | other | review | no |
| 3444 | [Agentic companion] Evict process-local companion sessions w | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3445 | [user-reported] behavior: User was unhappy about the compani | healthy | other | review | no |
| 3451 | [Agentic companion] Telegram: show generated images as nativ | healthy | other | review | no |
| 3452 | [Agentic companion] Weixin/WeChat: show generated images as  | healthy | other | review | no |
| 3453 | [Agentic companion] Define PromptTemplate dataclass for name | healthy | other | review | yes |
| 3454 | [Agentic companion] ds v4 toolcall 不生成 function call | healthy | other | review | no |
| 3456 | [Agentic companion] User chat must not go silent while tools | healthy | refactor | reparent_or_active | yes |
| 3457 | [Agentic companion] Deliver interim chat to OutputQueue whil | healthy | refactor | reparent_or_active | yes |
| 3458 | [Agentic companion] Prompt: brief user-facing line when star | healthy | refactor | reparent_or_active | yes |
| 3459 | [Agentic companion] Migrate non-chat triggers onto AgenticLo | healthy | refactor | reparent_or_active | yes |
| 3460 | Consolidate AgenticLoop direct user-turn modes and OutputQue | healthy | refactor | reparent_or_active | yes |
| 3463 | [Agentic companion] Bootstrap proactive chat should inject B | healthy | other | review | yes |
| 3465 | companion-harness: separate assistant-round events from deli | healthy | other | review | yes |
| 3466 | companion-harness: record non-queue bootstrap as backup-only | healthy | other | review | yes |
| 3467 | companion-harness: move user transcript persistence ownershi | healthy | other | review | yes |
| 3468 | [Agentic companion] AUTONOMY trace must affect follow-up use | healthy | other | review | yes |
| 3470 | [Agentic companion] Bootstrap interim replies should feel li | healthy | other | review | yes |
| 3471 | [Agentic companion] Token budget runtime state + config | healthy | ops_parked | comment_defer | yes |
| 3472 | [Agentic companion] Debit token budget at LLM completion bou | healthy | ops_parked | comment_defer | yes |
| 3473 | [Agentic companion] Gate autonomy and turns when token budge | healthy | ops_parked | comment_defer | yes |
| 3474 | [Agentic companion] Token budget: separate input vs output d | healthy | ops_parked | comment_defer | yes |
| 3476 | [Epic] agentic_companion — per-agent token usage budget | healthy | ops_parked | comment_defer | no |
| 3478 | Strip harness UTC timestamp prefixes from user-visible assis | healthy | other | review | no |
| 3479 | [Ops Telegram] Split multiline assistant replies into separa | healthy | other | review | no |
| 3485 | [Epic] ScopeQueueServing v1: continuous per-scope USER_CHAT  | healthy | refactor | reparent_or_active | no |
| 3487 | Channel inbound: enqueue + wake only (Weixin, App-WS remaini | healthy | refactor | reparent_or_active | yes |
| 3488 | AppWsChannelAdapter + one Coordinator per scope on presence | healthy | refactor | reparent_or_active | no |
| 3490 | Cleanup: remove queue USER_CHAT foreground_pending + tool-bg | healthy | refactor | reparent_or_active | yes |
| 3491 | Consistent identity across companion channels | healthy | other | review | no |
| 3493 | Weixin: migrate WeixinInprocessPresence to ScopeQueueServing | healthy | refactor | reparent_or_active | yes |
| 3500 | [Epic] Hermes channel adapter feature parity | healthy | other | review | no |
| 3501 | [Ops Telegram] Coalesce rapid inbound text before queue drai | healthy | other | review | no |
| 3502 | [Ops Telegram] Evaluate wrapping Hermes TelegramAdapter | healthy | other | review | no |
| 3504 | [Agentic companion] Cleanup: rename OutputQueue message_ids  | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3506 | [Agentic companion] MemoryStore: dedicated representation fo | healthy | other | review | yes |
| 3511 | [user-reported] other: Smoke test user-feedback issue (4bfa3 | duplicate | refactor | close | no |
| 3515 | [Agentic companion] Design output preferences for user-visib | healthy | product_blocked | comment_block | yes |
| 3516 | [Agentic companion] Simplify scope turn serialization and fo | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3521 | [Agentic companion] MemDoc-projected dynamic prompt composit | healthy | crs_blocked | comment_block | no |
| 3522 | [Agentic companion] Slot algebra: hierarchical memory compac | healthy | crs_blocked | comment_block | no |
| 3523 | [Agentic companion] Memory retrieval: resident / verbatim-wi | healthy | crs_blocked | comment_block | no |
| 3531 | [Epic] Telegram 付费投放上线前置门禁（仅 Telegram cohort） | healthy | other | review | no |
| 3532 | [Ops Telegram] 冷启动 onboard：implicit_sign_on_greeting + 英文默认文 | healthy | other | review | no |
| 3533 | [Ops Telegram] Onboard ACTIVE bond 门禁：坏状态不启动 presence | healthy | other | review | no |
| 3535 | [Ops Telegram] Launch 指标：proactive reciprocity 可衡量（API 或 SQL | healthy | other | review | no |
| 3542 | Weixin: converge inner-tick + tool-bg onto OutputQueue + con | healthy | refactor | reparent_or_active | no |
| 3543 | WS: converge inner-tick + tool-bg onto OutputQueue; remove D | healthy | refactor | reparent_or_active | no |
| 3547 | [Agentic companion] LivingSphere offline batch compact (cros | healthy | other | review | yes |
| 3548 | [Agentic companion] Rename Channel → Gateway in companion_ha | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3549 | [Agentic companion] Consolidate MemDoc type definitions (nam | healthy | other | review | yes |
| 3550 | [Agentic companion] Dreaming batch: Postgres advisory lock p | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3551 | [Agentic companion] Dreaming batch LangSmith span cleanup on | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3552 | [Agentic companion] Atomic append for companion user feedbac | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3553 | [Agentic companion] Hoist langsmith_slice into TurnDeps | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3561 | [Epic] Harness scripted orchestration e2e follow-up (#3559) | healthy | other | review | no |
| 3564 | [HITL] Real-model real-gateway harness smoke (noci tier) | healthy | other | review | no |
| 3565 | [AFK] CompanionLLMClient provider-error unit tests (scripted | healthy | other | review | no |
| 3566 | [Agentic companion] Token 预算耗尽时在上行入队前拦截用户消息 | duplicate | refactor | close_merge_parent | no |
| 3567 | [Agentic companion] Token 预算暂停：分层停止 companion 执行 | duplicate | refactor | close_merge_parent | no |
| 3568 | [Companion WS] 接入订阅聊天限额 check_chat_limit / record_usage | duplicate | refactor | close_merge_parent | no |
| 3580 | Migrate maintenance/autonomy inner ticks to single-LLM Agent | healthy | refactor | reparent_or_active | yes |
| 3593 | [user-reported] tool_failure: 用户要求查询实时天气，但 Google CSE 环境变量未配 | healthy | other | review | no |
