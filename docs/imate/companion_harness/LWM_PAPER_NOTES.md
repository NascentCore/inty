# Qwen-AgentWorld (LWM) — relevance notes for Inty

**Generated entirely by Cursor Cloud Agent** (pointer doc after closing unmerged PR #3643).

## Paper

- [Qwen-AgentWorld: Language World Models for General Agents](https://arxiv.org/pdf/2606.24597) (arXiv:2606.24597)

Language World Model (LWM): learn **(history, action) → next environment observation** across agent domains (Terminal, MCP, Search, SWE, GUI, …). Training: **CPT → SFT (explicit next-state thinking) → RL** with AgentWorldBench rubric rewards including **Consistency** (cross-turn state coherence).

## Inty mapping (high level)

- **Not the same problem**: paper optimizes **tool/agent environment simulation**; Inty TechnoCore / LivingSphere / AUTONOMY optimize **companionship virtual life** + real tools, explicitly **not** a neural world simulator (`techno_core/DESIGN.md` non-goals).
- **Useful idea (indirect)**: close **experience → hidden state** feedback (e.g. `techno_core_events.jsonl` reader + curation) — see [`FR_WORLD_ENGINE.md`](./FR_WORLD_ENGINE.md) §1.
- **Paper Consistency** = train-time reward on predicted observations vs trajectory history. **Not** the same as a prompt checklist on `LIFE_CURRENTS.md`.

## Local REPL experiment (2026-06-24, unmerged prototype)

Explored three **prompt-only** toggles on inner-tick **AUTONOMY** only (`state_consistency`, `experience_state_loop`, `mental_simulation`). Driver was on branch `cursor/lwm-autonomy-experiments-538a` (closed, not merged).

**Setup**: Ops `:8001`, `devops/config.yaml.local`, bootstrap script + 75s idle + probe USER_CHAT: 「你最近在虚拟环境里做什么？」

| Variant | Takeaway |
| --- | --- |
| **baseline** | Rich `LIFE_CURRENTS.md` + TC events written, but USER_CHAT answered 「刚醒来几分钟」— **USER_CHAT does not inject LIFE_CURRENTS** (AUTONOMY MVP). |
| **state_consistency** (prompt checklist vs USER/MEMORY/LIVING_SPHERE) | Best **hidden-state** alignment (e.g. 雨声资料阁 + Godot + matching TC event); probe sometimes mentioned virtual space. |
| **experience_state_loop** (inject TC event tail) | Slight gain on write-side (+4ch); probe still pivoted to Godot chat only. |
| **mental_simulation** (`【预测】` before tools) | Retry: honest API-failure notes in `LIFE_CURRENTS`; probe inconclusive (LLM 500). |
| **all_three** | Shorter/weaker `LIFE_CURRENTS` (193ch); off-topic probe — **stacking slices hurt**. |

**Blockers**: local `google_web_search` API unconfigured; AUTONOMY inner-tick ran (`transcript_inner_tick` versions present) but user-visible track does not read autonomy state.

**Conclusion**: **Not worth shipping** LWM-style prompt experiments as product harness. Prefer closing the **techno_core_events → hidden state** loop in code over inference-time AUTONOMY checklists. Revisit only if PROACTIVE_CHAT or controlled USER hint path is in scope.

## Related Inty docs

- [`AUTONOMY.md`](./AUTONOMY.md) — AUTONOMY track; MVP: no `USER_CHAT` LIFE_CURRENTS injection
- [`FR_WORLD_ENGINE.md`](./FR_WORLD_ENGINE.md) — evolvable hidden state; events reader gap
- [`techno_core/DESIGN.md`](../../app/techno_core/DESIGN.md) — no world simulator non-goals
