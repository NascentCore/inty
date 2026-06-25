# Companion harness issue audit 2026-06-25

Cron consolidation run. Scope: companion harness issues + inline TODO refs.

| # | title | class | lane | action | TODO |
|---|-------|-------|------|--------|------|
| 211 | [Cleanup] 使用基本的 openai sdk+langsmith-tracing 来做聊天的生成 | stale | hygiene_defer | close_or_ping | no |
| 312 | [BUG] Langsmith tracing shows too much nested invocations | stale | other | close_or_ping | no |
| 2193 | 【后端系统 Bug】langsmith trace 数量明显少于系统规模 | healthy | other | review | no |
| 2229 | 【后端系统 Bug】似乎是首次大模型调用时，会有较高的延时 | healthy | other | review | no |
| 3025 | [Agentic companion]  Sometime the LLM returns no outputs, see Langsmith run of no outpu... | healthy | other | review | no |
| 3113 | chat WS: turn_lock 内 await 伴侣回合阻塞 user_signed_out 等控制帧 | healthy | other | review | no |
| 3123 | [Agentic companion] 连续快速发消息：用 transcript 轮次状态取代 tool_bg_idle 阻塞/抢占 | healthy | other | review | yes |
| 3158 | Companion WS: 前台 assistant_text 为空但 tool_background 已启动时仍返回 500 Chat returned no content | healthy | other | review | no |
| 3207 | Companion WS completion: adopt typed Pydantic wire models (Phase 2+) | healthy | other | review | no |
| 3209 | [Agentic companion] WebSocket downlink for user-turn UserVisibleChunk (#3402) | healthy | other | review | yes |
| 3211 | Collapse WS companion outbound into CompanionPresenceSession downlink | healthy | other | review | yes |
| 3252 | [Agentic companion] 强化自主性：trivial 用户消息不应让 agent 弃场（被轻易拉出自己正在进行的 activity） | healthy | other | review | no |
| 3256 | [Agentic companion] WS disconnect mid-turn: persist-first with delivery state | healthy | other | review | yes |
| 3268 | 有些模型 temp=0 也会有输出变动 | healthy | other | review | no |
| 3269 | DS v3.2 不支持同时设置 output-format & tool-calls | healthy | other | review | no |
| 3271 | [Agentic companion] Dreaming cluster mutex for multi-process backend | healthy | other | review | yes |
| 3273 | Inner-tick poll: try all due tracks per wake (not single-slot priority) | healthy | other | review | yes |
| 3285 | [Agentic companion] Proactive + dual-LLM foreground deny image gen while tool_backgroun... | healthy | other | review | yes |
| 3293 | Companion multimodal user-turn + Weixin inbound image support | healthy | other | review | yes |
| 3314 | [Agentic companion] Centralize session background task cleanup | healthy | hygiene_defer | no_ready_for_agent | no |
| 3318 | [Agentic companion] Wrap Hermes WeixinAdapter behind Inty-owned channel adapter | healthy | hygiene_defer | no_ready_for_agent | no |
| 3323 | [Epic] agentic_companion — Reddit 调研：trust / continuity / retention | healthy | refactor | reparent_or_active | no |
| 3325 | [Agentic companion] Memory visibility：用户可查看并纠正 companion 记忆 | healthy | product_blocked | comment_block | yes |
| 3326 | [Agentic companion] Update transparency：model/deploy 变更用户可见说明 | healthy | product_blocked | comment_block | no |
| 3327 | [Agentic companion] Proactive check-in grounded in memory | healthy | other | review | no |
| 3328 | [Agentic companion] Bootstrap: relationship seed + experience framing (functional → bon... | healthy | other | review | no |
| 3329 | [Agentic companion] Personality / memory stability harness 加固 | healthy | product_blocked | comment_block | no |
| 3330 | [Agentic companion] Trust / continuity narrative（onboarding & copy） | healthy | product_blocked | comment_block | no |
| 3331 | [Agentic companion] Reddit listening cadence（可选） | healthy | product_blocked | comment_block | no |
| 3334 | cleanup: remove agent status_line (chat header tagline) | healthy | hygiene_defer | no_ready_for_agent | no |
| 3338 | [Ops Telegram demo] Unify presence lifecycle with ensure_presence | healthy | other | review | no |
| 3339 | [Ops Telegram demo] Parallel per-binding restore on Ops startup | healthy | other | review | no |
| 3340 | [Ops Telegram demo] User unbind flow (wire delete_binding) | healthy | other | review | no |
| 3341 | Epic: Companion Relationship System (CRS) — psychology × time frames × harness | healthy | refactor | reparent_or_active | yes |
| 3342 | Companion companionship doc + Turn Brief plumbing (Phase A foundation, no UX change) | healthy | crs_blocked | comment_block | no |
| 3343 | Activate companionship prompt + Turn Brief turn_recall + dreaming curator (Phase B) | healthy | other | review | yes |
| 3344 | Extended relationship psychology fields (Phase C: bids, trust, repair) | healthy | other | review | no |
| 3345 | [Agentic companion] Doc: relationship state glossary (current code vs #3341 target) | healthy | other | review | no |
| 3346 | [Agentic companion] Skills: inspect companionship state (session_phase, tone, context_m... | healthy | other | review | no |
| 3347 | [Ops Telegram demo] Webhook mode (replace getUpdates long-poll) | healthy | other | review | no |
| 3348 | [Ops Telegram demo] Public /telegram onboard (productize beyond /telegram-demo) | healthy | other | review | no |
| 3349 | [Ops Telegram demo] Inbound non-text messages (photo, voice, sticker) | healthy | other | review | no |
| 3350 | [Agentic companion] Unify runtime channel registry (App WS, Weixin, Telegram) | healthy | other | review | no |
| 3351 | [Agentic companion] Extend ws_channel_guard to Weixin bridge | healthy | other | review | no |
| 3359 | Clarify Agent ORM field ownership: legacy character card vs companion production rows | healthy | hygiene_defer | no_ready_for_agent | no |
| 3361 | Telegram dedicated-bot bonding: 1 user : 1 bot : 1 agent (triage portal) | healthy | other | review | yes |
| 3362 | companion: channel-specific tools (filter by runtime channel + adapter dispatch) | healthy | other | review | yes |
| 3365 | Doc: SDCM + time frames + write lattice (CRS L0 canon) | healthy | crs_blocked | comment_block | no |
| 3366 | Optional long-cycle relationship reflection curator (CRS L1) | healthy | crs_blocked | comment_block | no |
| 3367 | TrackWritePolicy registry: time frame × CompanionTurnTrack × MemoryDoc allowlist (CRS L3) | healthy | crs_blocked | comment_block | yes |
| 3369 | [Agentic companion] Configurable user-turn LLM loop: dual_llm vs in_turn_single_llm (bo... | healthy | other | review | yes |
| 3373 | [Epic] agentic_companion — autonomous runtime (presence-less inner-tick) | healthy | refactor | reparent_or_active | no |
| 3374 | [Agentic companion] Pausable autonomous runtime (token budget pause/resume) | healthy | ops_parked | comment_defer | no |
| 3375 | [Agentic companion] Narrow monolog inner-tick to ai_private.jsonl append (legacy MAINTE... | healthy | other | review | yes |
| 3376 | [Agentic companion] Dreaming day rollup: merge inner-tick material into consolidation | healthy | other | review | yes |
| 3377 | [Agentic companion] Inner-tick fire: shared delivery assembly (ws_turn_support dedup) | healthy | hygiene_defer | no_ready_for_agent | no |
| 3381 | [user-reported] memory: You keep getting my timezone wrong. | healthy | other | review | no |
| 3390 | [Agentic companion] Generic IDENTITY.md package template seeds USER + agent runtime docs | healthy | other | review | yes |
| 3391 | [agentic_companion] User time context: inference hardening (transcript, logging, struct... | healthy | other | review | yes |
| 3393 | [Epic] agentic_companion — explicit turn orchestration (Pie-inspired) | overlap | refactor | comment_superseded | no |
| 3394 | [Epic] agentic_companion — async multi-level task orchestration (sub-tasks, sub-agents) | overlap | refactor | comment_superseded | no |
| 3395 | [Epic] Telegram channel: Bots API options to hook agents | healthy | refactor | reparent_or_active | no |
| 3396 | [Ops Telegram] Shared-bot routing (Option A): current path & meta-op constraints | healthy | other | review | no |
| 3397 | [Companion] Telegram Bots API meta-operations as channel tools | healthy | other | review | yes |
| 3398 | [Epic] agentic_companion — dual-LLM vs single-LLM user-turn | healthy | refactor | reparent_or_active | yes |
| 3401 | [Agentic companion] Separate CompanionTurnTrack from AgenticLoopMechanism | healthy | other | review | yes |
| 3402 | [Agentic companion] UserVisibleChunk harness contract (decoupled channel downlink) | healthy | other | review | yes |
| 3405 | [Agentic companion] Design conceptual & logical memory hierarchy | healthy | other | review | yes |
| 3407 | Converge transcript.jsonl assistant rows to shared Pydantic write model | healthy | other | review | no |
| 3409 | [Agentic companion] Reorganize companion/ flat modules into companion_harness sub-packages | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3411 | [agentic_companion] Telegram user timezone: manual E2E smoke + LangSmith acceptance | healthy | other | review | yes |
| 3413 | [Agentic companion] Centralize MemoryDoc relative path constants (replace scattered lit... | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3417 | [Agentic companion] Deduplicate core template seeding with PromptSliceId | healthy | hygiene_defer | no_ready_for_agent | no |
| 3423 | [Agentic companion] Scope inner-tick: due-scope filter (#3255 follow-up) | healthy | other | review | yes |
| 3424 | [Agentic companion] Scope inner-tick: dedup presence/scope fire glue | healthy | hygiene_defer | no_ready_for_agent | no |
| 3426 | [Agentic companion] Scope inner-tick: integration test for kernel fire path | healthy | other | review | no |
| 3433 | [user-reported] tool_failure: Internal chain of thought (thoughts from previous Proacti... | healthy | other | review | no |
| 3434 | [user-reported] tool_failure: The user pointed out that the AI hallucinated the success... | healthy | other | review | no |
| 3435 | [user-reported] behavior: The user complained about a sudden change in moral boundaries... | healthy | other | review | no |
| 3436 | [user-reported] behavior: User is frustrated and feels cheated ('骗子啊') because of the c... | healthy | other | review | no |
| 3437 | [user-reported] behavior: User reports that the rhythm and timing of proactive chat fee... | healthy | other | review | no |
| 3438 | [user-reported] behavior: 用户指出主动聊天的节奏感不好，跟当前的感觉对不上，需要提供一种自适应的调整闭环。 | healthy | other | review | no |
| 3440 | [Epic] Channel-specific input and output message affordances | healthy | refactor | reparent_or_active | no |
| 3441 | [Agentic companion] Telegram: emoji reactions and reply-to messages | healthy | other | review | no |
| 3442 | [Agentic companion] Weixin/WeChat: emoji reactions and reply-to messages | healthy | other | review | no |
| 3444 | [Agentic companion] Evict process-local companion sessions when scope has no active pre... | healthy | other | review | yes |
| 3445 | [user-reported] behavior: User was unhappy about the companion blending their AI profes... | healthy | other | review | no |
| 3451 | [Agentic companion] Telegram: show generated images as native image messages | healthy | other | review | no |
| 3452 | [Agentic companion] Weixin/WeChat: show generated images as native image messages | healthy | other | review | no |
| 3453 | [Agentic companion] Define PromptTemplate dataclass for named-slot prompt rendering | healthy | other | review | yes |
| 3454 | [Agentic companion] ds v4 toolcall 不生成 function call | healthy | other | review | no |
| 3456 | [Agentic companion] User chat must not go silent while tools execute | healthy | other | review | yes |
| 3457 | [Agentic companion] Deliver interim chat to OutputQueue while tool loop runs | healthy | other | review | yes |
| 3458 | [Agentic companion] Prompt: brief user-facing line when starting tool calls | healthy | other | review | yes |
| 3459 | [Agentic companion] Migrate non-chat triggers onto AgenticLoop | healthy | other | review | yes |
| 3460 | Consolidate AgenticLoop direct user-turn modes and OutputQueue | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3463 | [Agentic companion] Bootstrap proactive chat should inject BOOTSTRAP.md | healthy | other | review | yes |
| 3465 | companion-harness: separate assistant-round events from delivery policy | healthy | other | review | no |
| 3466 | companion-harness: record non-queue bootstrap as backup-only legacy path | healthy | hygiene_defer | no_ready_for_agent | no |
| 3467 | companion-harness: move user transcript persistence ownership out of shared single-LLM ... | healthy | hygiene_defer | no_ready_for_agent | no |
| 3468 | [Agentic companion] AUTONOMY trace must affect follow-up user chat (019ed438) | healthy | other | review | yes |
| 3470 | [Agentic companion] Bootstrap interim replies should feel like chatting while working, ... | healthy | other | review | yes |
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
| 3490 | Cleanup: remove queue USER_CHAT foreground_pending + tool-bg consumer | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3491 | Consistent identity across companion channels | healthy | other | review | no |
| 3493 | Weixin: migrate WeixinInprocessPresence to ScopeQueueServing enqueue+wake | healthy | other | review | yes |
| 3500 | [Epic] Hermes channel adapter feature parity | healthy | refactor | reparent_or_active | no |
| 3501 | [Ops Telegram] Coalesce rapid inbound text before queue drain (Hermes parity) | healthy | other | review | no |
| 3502 | [Ops Telegram] Evaluate wrapping Hermes TelegramAdapter | healthy | other | review | no |
| 3504 | [Agentic companion] Cleanup: rename OutputQueue message_ids JSON column | healthy | hygiene_defer | no_ready_for_agent | no |
| 3506 | [Agentic companion] MemoryStore: dedicated representation for static prompt-slice markdown | healthy | other | review | yes |
| 3515 | [Agentic companion] Design output preferences for user-visible tracks | healthy | other | review | yes |
| 3516 | [Agentic companion] Simplify scope turn serialization and foreground-pending rules | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3521 | [Agentic companion] MemDoc-projected dynamic prompt composition | healthy | other | review | no |
| 3522 | [Agentic companion] Slot algebra: hierarchical memory compaction for the dreaming loop | healthy | crs_blocked | comment_block | no |
| 3523 | [Agentic companion] Memory retrieval: resident / verbatim-window / associative tiers | healthy | other | review | no |
| 3531 | [Epic] Telegram 付费投放上线前置门禁（仅 Telegram cohort） | healthy | refactor | reparent_or_active | no |
| 3532 | [Ops Telegram] 冷启动 onboard：implicit_sign_on_greeting + 英文默认文案 | healthy | other | review | no |
| 3533 | [Ops Telegram] Onboard ACTIVE bond 门禁：坏状态不启动 presence | healthy | other | review | no |
| 3535 | [Ops Telegram] Launch 指标：proactive reciprocity 可衡量（API 或 SQL/脚本） | healthy | other | review | yes |
| 3536 | [Ops Telegram] 付费广告 flight：薄版暂停 playbook + pre-flight checklist | healthy | other | review | no |
| 3537 | [Ops Telegram] Cohort 复盘模板（第一批 reciprocators 前完成） | healthy | other | review | no |
| 3542 | Weixin: converge inner-tick + tool-bg onto OutputQueue + continuous pump (!3493) | healthy | other | review | no |
| 3543 | WS: converge inner-tick + tool-bg onto OutputQueue; remove Downlink module (#3210/#3398) | healthy | other | review | no |
| 3547 | [Agentic companion] LivingSphere offline batch compact (cross-scope backfill) | healthy | other | review | yes |
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
| 3586 | Remove temporary default_user_time_zone launch fallback after per-user timezone is reli... | healthy | other | review | yes |
| 3588 | Extend reply-language runtime clause to legacy non-AgenticLoop user-turn paths | healthy | other | review | yes |
| 3593 | [user-reported] tool_failure: 用户要求查询实时天气，但 Google CSE 环境变量未配置导致搜索功能不可用，无法提供可核验的公开信息。 | healthy | other | review | no |
| 3596 | [Agentic companion] Dual-LLM user turn: dedupe overlapping foreground + tool_background... | healthy | other | review | no |
| 3597 | [user-reported] behavior: In-session denial ignored — batch/status re-ask loop (Telegra... | healthy | other | review | no |
| 3601 | Companion：拆分 INNER_TICK_SCHEDULED 与 PROACTIVE_CHAT 的 InnerTickActivity 映射 | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3602 | ProactiveChatEnvelope：评估 OpenAI SDK completions.parse 替代手工 JSON 解析 | healthy | other | review | yes |
| 3605 | [Ops Telegram] Launch gate: verify English companion replies for paid-ads cohort | healthy | other | review | no |
| 3606 | REPL regression：将 live driver 与 LLM 行为 eval 分层 | healthy | other | review | no |
| 3613 | [user-reported] memory: 用户位于美国西海岸，但多啦在描述天气/时间时完全没考虑时区，默认了 Asia/Shanghai，让用户感到被忽视。 | healthy | other | review | no |
| 3617 | [user-reported] behavior: Companion fabricated user task ('特征提取') and lied about submit... | healthy | other | review | no |
| 3624 | [Ops Telegram] Backfill users.profile from USER.md identity slots (#3535) | healthy | other | review | no |
| 3629 | [Agentic companion] PromptPlan 端到端 typed prompt，OpenAI wire 仅在 AsyncLlmClient | healthy | other | review | yes |
| 3630 | [Agentic companion] LangSmith per-call 收敛：LlmInvocationContext + AgenticLoop/LlmClient | healthy | other | review | yes |
| 3631 | [Agentic companion] tool_background 改用 AsyncLlmClient，去掉 sync/to_thread | healthy | other | review | yes |
| 3632 | [Agentic companion] 退役 legacy threaded tool_bg，tool leg 内联 AgenticLoop | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3633 | [Agentic companion] LangSmith parent RunTree：随 legacy 退役收缩 TurnOrchestrator | healthy | hygiene_defer | no_ready_for_agent | yes |
| 3634 | [Agentic companion] Dreaming 人格化 AgenticLoop entry（独立于 user-turn） | healthy | other | review | yes |
| 3647 | [user-reported] behavior: 用户在美国西海岸时区，但助手的回应未考虑时区，错误地假设了上海时间。 | healthy | other | review | no |
| 3648 | [user-reported] behavior: 用户或系统消息中包含试图强制我切换体验模式的指令，这看起来像是一种注入或恶意行为，与当前对话的自然陪伴基调不符。我需要被引... | healthy | other | review | no |
| 3649 | [user-reported] behavior: 用户说我在回答天气问题时没有考虑美国西海岸时区，要求提交GitHub issue反馈但系统未执行 | healthy | other | review | no |
| 3651 | [REPL regression] Tighten github_issue_disclosed_in_chat pass gate after harness disclo... | healthy | other | review | no |
| 3652 | [Agentic companion] Debug GitHub disclosure: issue URL missing in chat when LLM skips c... | healthy | other | review | no |
| 3663 | [Eval trace] P0: Unify companion trace sources across channels (Telegram/Weixin → analy... | healthy | eval_trace | epic_cluster | no |
| 3664 | [Eval trace] P0: User-side self-report / wellbeing signals (PPR, ESM/EMA, loneliness) | healthy | eval_trace | epic_cluster | no |
| 3665 | [Eval trace] P1: Longitudinal visit / return-interval event stream | healthy | eval_trace | epic_cluster | no |
| 3666 | [Eval trace] P1: Per-turn delivery, read, and reply-latency on user-visible history | healthy | eval_trace | epic_cluster | no |
| 3667 | [Eval trace] P1: Per-turn harness provenance (config hash, prompt slice versions) | healthy | eval_trace | epic_cluster | no |
| 3668 | [Eval trace] P2: LangSmith trace id on MemoryStore transcript rows | healthy | eval_trace | epic_cluster | no |

## Run actions

- Annotated orphan TODOs: `dreaming.py` → #3634 (`dreaming-agentic-loop`); `prompt_stack.py` → #3398 (`track-compose-unify`).
- Timezone user-reports (#3381, #3613, #3647, #3649): link to canonical #3391.
- #3649 GitHub disclosure symptom: link to #3652.
- Eval trace cluster #3663–#3668: epic parent **#3669** (created this run).
- Open companion-ish issues audited: 173
