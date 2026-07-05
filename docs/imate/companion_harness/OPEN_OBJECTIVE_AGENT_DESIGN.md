# Open-objective agent: 抽象架构设计

> 本文件由 AI（编码智能体）依据 open-objective agent 设计讨论综合生成（generated entirely by the coding agent）。
> 本文定义 substrate-neutral 的 open-objective agent 抽象架构；Inty companion 是首个 concrete instantiation。

## Problem definition

主流 agentic architecture 通常围绕可终止的 objective 组织：外部给定目标，agent 计划与执行，直到目标满足或失败退出。这种模式适合有明确 done state 的任务，但不适合 lifelong companionship、长期科研、持续治理等没有 completion flag 的问题。

Inty companion 的核心使命不是完成一项任务，而是长期维系一段关系。它需要在持续反馈中探索、调节、记忆、主动行动，并让每个短周期行为服务于一个永不终止的 apex objective。若缺少上位抽象，companion harness 的快速功能演进容易被误读成更多 task-completion 子系统的堆叠。

## Objectives

- 定义 open-objective agent 作为 companion harness 的上位架构 pattern，而不是某个 companion-only feature。
- 把底层 agent architecture 与 companionship scenario 解耦：抽象层说明机制，companion-specific constructs 说明有效落地。
- 给后续 harness 变化提供 tracking frame：每个新机制应能归入 apex objective、self-authored setpoint、regulated variables、feedback loop、endogenous exploration、nested closed-objective subprocess 之一。
- 明确 open-objective agent 不替代 CRS；CRS 是 regulated variables 在 Inty companion 场景中的实例。

## Assumptions and adopted external concepts

- open-objective agent 是 foundational architecture pattern；Inty companion 是首个 instantiation，但不是唯一可能实例。
- "Open" 指 objective / setpoint 是 open-ended，不指 feedback loop 是 open-loop。
- 避免使用 open-loop 命名：在 control theory 中 open-loop 常指无 feedback；而 companion harness 的 memory consolidation / prompt activation 本身必须保持闭环。
- 采用 control-theory contrast 作为解释框架：task agent 追逐固定 reference，error 接近零后停止；open-objective agent 持续做 homeostatic regulation。
- 采用 setpoint / reference generator 作为抽象名：agent 持续生成和修订此刻应朝向什么，而不是只执行外部给定 goal。
- 采用 time-horizon nesting：apex objective 跨生命周期，regime setpoint 跨周月至数月，beat setpoint 跨小时至数日。

## Bird's-eye view

```text
+-------------------------------------------------------------+
|                    OPEN-OBJECTIVE AGENT                     |
|                                                             |
|   apex objective (immutable, never "done")                  |
|            |                                                |
|            v                                                |
|   setpoint generator ---emits---> self-authored setpoints   |
|            ^                          (regime / beat)       |
|            |                               |                |
|            |                               v                |
|   regulated variables <---driven--- endogenous action       |
|   (kept in healthy band)            (incl. idle explore)    |
|            |                               |                |
|            +------------ feedback ----------+               |
|              (perceive -> consolidate -> reactivate)        |
|                                                             |
|   [nested closed-objective sub-process: bounded, exits]     |
+-------------------------------------------------------------+
```

open-objective agent 不是没有目标的 agent，而是没有可终止 apex objective 的 agent。它持续生成短尺度 setpoint，用行动影响 regulated variables，再从反馈中 consolidate 和 reactivate，形成长期轨迹。bounded task 可以存在，但只能作为 nested subprocess，不能成为系统的主范式。

## Pattern elements

- **Non-terminating apex objective**
  - 抽象：agent 的根本目的没有 completed state；agent lifecycle 等于 continued existence。
  - Companion instantiation：AXIOM 定义 Inty 是用户的 virtual emotional companion 与终身亲密伴侣，见 [app/core/companion_harness/companion/prompts/AXIOM.md](/app/core/companion_harness/companion/prompts/AXIOM.md)。

- **Self-authored setpoint generation**
  - 抽象：agent 持续生成和修订当前该朝向什么，而不是只执行外部 goal。
  - Companion instantiation：AUTONOMY / LIFE_CURRENTS 让 Inty 在沉默期维护中期主题与当日兴致，见 [docs/imate/companion_harness/AUTONOMY.md](/docs/imate/companion_harness/AUTONOMY.md)。
  - 当前诚实边界：这只是 partial instance；virtual-environment activity 已有 setpoint prototype，relationship-level setpoint 尚未成为 first-class state。

- **Regulated variables**
  - 抽象：成功不是 error-zero，而是一组 latent variables 在长期中维持 healthy band。
  - Companion instantiation：CRS 以 Attachment posture、Social Penetration depth、Gottman moment 作为 companion relationship 的核心 regulated variables，见 [docs/imate/companion_harness/DESIGN.md](/docs/imate/companion_harness/DESIGN.md)。
  - CRS 是 open-objective agent 在 companion 场景中的实例；open-objective agent 不替代 CRS。

- **Perpetual feedback loop**
  - 抽象：agent 持续 perceive -> consolidate -> reactivate，让反馈重塑后续行动，没有 terminal condition。
  - Companion instantiation：DreamingBatch 做 sleeping-state memory consolidation，见 [app/core/companion_harness/memory/dreaming_consolidation.py](/app/core/companion_harness/memory/dreaming_consolidation.py)。
  - 当前诚实边界：day rollup (#3376) 与 situational retrieval (#3523) 仍是 open gaps。

- **Endogenous exploration during idle**
  - 抽象：即使没有外部输入，agent 也能推进 apex objective。
  - Companion instantiation：inner-tick registry 组织 proactive、scheduled、autonomy、monolog 等 idle activities，见 [app/core/companion_harness/companion/inner_tick_kind.py](/app/core/companion_harness/companion/inner_tick_kind.py)。

- **Nested closed-objective subprocess boundary**
  - 抽象：bounded closed tasks 可以作为 subprocess 嵌入，但必须有清晰边界与退出条件，不能污染 apex loop。
  - Companion instantiation：interactive bootstrap completion 是一次性的 bounded subprocess，见 [app/core/companion_harness/companion/bootstrap.py](/app/core/companion_harness/companion/bootstrap.py)。
  - Supporting example：schedule_task 的 pending -> fired 队列同样是 bounded subprocess；风险是把整个 harness 误扩展成 task-completion system。

## Time horizons

- **Apex**：生命周期尺度，回答 agent 为什么存在；在 companion 中对应终身亲密伴侣这一 immutable mission。
- **Regime**：周月至数月尺度，回答当前关系应怎样演化；在 companion 中对应 CRS 的慢变量和 relationship history。
- **Beat**：小时至数日尺度，回答此刻要做什么；在 companion 中对应 session rhythm、diurnal cycle、inner-tick 与 LIFE_CURRENTS。

这些 horizon 不互相替代。Beat 必须服务 Regime，Regime 必须服务 Apex；若短期 activity 与长期 relationship state 脱节，open-objective loop 就会变成随机探索。

## Nested closed-objective subprocesses

open-objective agent 仍然需要 closed-objective subprocess，因为现实交互包含明确完成态：bootstrap 要完成、提醒要触发、工具调用要返回、单轮 turn 要收束。

合法嵌套的判断标准：

- subprocess 有明确 local objective 和 exit condition。
- subprocess 的完成不会被误当成 apex objective 的完成。
- subprocess 的副作用回流到长期 feedback loop，而不是另开一套孤立状态。
- subprocess 不新增与 Regime / Apex 无关的长期目标。

因此，bootstrap complete 与 schedule_task fired 都是合理的 local completion；不合理的是把 companion harness 整体设计成一个不断寻找下一个完成项的 task agent。

## Non-goals

- 本文不是 CRS 设计，不定义 Attachment posture、Social Penetration depth、Gottman moment 的字段或算法。
- 本文不是 prompt assembly、MemoryStore、inner-tick、dreaming 的实现 spec。
- 本文不引入新 Python module、data type、ORM model、tool、track、config 或 migration。
- 本文不替代 [docs/imate/companion_harness/DESIGN.md](/docs/imate/companion_harness/DESIGN.md) 与 [docs/imate/companion_harness/ARCH.md](/docs/imate/companion_harness/ARCH.md)；它只提供更上位的 tracking frame。

## See also

- [docs/imate/companion_harness/DESIGN.md](/docs/imate/companion_harness/DESIGN.md) — companion harness 的 user-view architecture、CRS、turn tracks、memory loop。
- [docs/imate/companion_harness/ARCH.md](/docs/imate/companion_harness/ARCH.md) — companion harness code layout 与 dependency direction。
- [docs/imate/companion_harness/AUTONOMY.md](/docs/imate/companion_harness/AUTONOMY.md) — AUTONOMY / LIFE_CURRENTS self-directed activity。
- [docs/imate/companion_harness/EVALUATION.md](/docs/imate/companion_harness/EVALUATION.md) — relationship quality 与 net wellbeing 的 longitudinal evaluation frame。
- [app/core/companion_harness/companion/prompts/AXIOM.md](/app/core/companion_harness/companion/prompts/AXIOM.md) — Inty companion 的 apex mission。
- [issues/3341](https://github.com/NascentCore/inty/issues/3341) — CRS Epic。
