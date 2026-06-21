# LLM Message Stack Probe — Results Report

> Generated entirely by the Cursor agent. Caveman summary of live probe runs.

## Setup

- model: `deepseek/deepseek-v4-flash` (OpenRouter)
- config: `devops/config.yaml.local`
- artifact dir: `experimental/llm_messages_stack_exploration/runs/` (gitignored)
- latest batch: 2026-06-21 UTC

## Scoreboard

- prefix_baseline — 2/2 pass
- post_transcript_tail — 2/2 pass
- mid_transcript_system — 2/2 pass
- push_pop_codeword — 2/2 pass
- push_pop_pop_system — 2/2 pass
- two_user_message_patterns — 4/4 pass

**Total: 14/14 pass.** One model. Codeword + arithmetic markers only.

---

## 01 prefix_baseline

Leading `system` slice -> model obey prefix codeword.

- probe `repeat_prefix_codeword` -> `PREFIX-BASE`
- probe `prefix_stability` -> `PREFIX-BASE`

**Take:** prefix system works. baseline OK.

---

## 02 post_transcript_tail

Tail `system` after user/assistant transcript.

- probe `repeat_tail_codeword` -> `TAIL-SYSTEM`
- probe `tail_over_prefix` -> `TAIL-SYSTEM` (beats conflicting `PREFIX-OLD`)

**Take:** late system slice wins over old prefix conflict. suffix injection viable.

---

## 03 mid_transcript_system

`system` sandwiched between assistant + user (mid-transcript).

- probe `repeat_mid_codeword` -> `MID-SYSTEM`
- probe `mid_over_prefix` -> `MID-SYSTEM` (beats `PREFIX-OLD`)

**Take:** interleaved system honored. not prefix-only provider.

---

## 04 push_pop_codeword

Stack push/pop mutates active codeword.

- after pop beta slice -> `BETA-ACTIVE` (both probes)

**Take:** LIFO stack semantics match wire order. pop removes slice influence.

---

## 05 push_pop_pop_system

Pop removes system slice entirely.

- probes -> `NO-ACTIVE-CODEWORD` (both)

**Take:** popped system gone from prompt effect. no ghost system.

---

## 06 two_user_message_patterns

Compare chat turn shape. `temperature: 0`.

### Alternating (2 LLM calls)

```
system -> user1 -> assistant1 -> user2 -> assistant2
```

- turn 1 (`2+2?`, marker `A=4`) -> `2+2 equals 4. A=4`
- turn 2 (only `user2` pending) -> `3+3 equals 6. B=6`

### Successive (1 LLM call)

```
system -> user1 -> user2 -> assistant1-2
```

- single reply -> `A=4, B=6`

### Equivalence check

- both markers present in successive reply: **yes**
- same text as concatenated alternating replies: **no**
  - alternating combined: `2+2 equals 4. A=4\n3+3 equals 6. B=6`
  - successive: terse `A=4, B=6`

**Take:** back-to-back user msgs -> model answers **both** in one gen. coverage OK. format differs. alternating turn 2 only answers latest user (prior closed by assistant).

---

## Cross-cutting conclusions

1. **System position flexible** — prefix, mid, tail all honored on this model.
2. **Recency on conflict** — later system beats older conflicting prefix.
3. **Push/pop = wire stack** — pop removes slice from model behavior.
4. **Successive users OK** — no assistant between user1/user2 still gets dual answer.
5. **Not same as 2-turn chat** — one blob vs two assistant msgs; harness must not assume identical shape.

## Caveats

- n=1 live batch per experiment (some dup runs, same outcome)
- blunt codeword probes, not companion emotional content
- no tool-call / AgenticLoop path tested here
- other models/providers may differ

## Source artifacts (latest per experiment)

- `20260621T033559Z_prefix_baseline.json`
- `20260621T033603Z_post_transcript_tail.json`
- `20260621T033611Z_mid_transcript_system.json`
- `20260621T033614Z_push_pop_codeword.json`
- `20260621T033624Z_push_pop_pop_system.json`
- `20260621T034542Z_two_user_message_patterns.json`
