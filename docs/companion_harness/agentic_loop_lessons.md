# Agentic loop outbound — Design v2 lessons

## Summary

Agentic loop user-visible output uses a **single pull pipeline**:

- **Harness** — ``AgenticLoop`` / ``run_agentic_loop`` enqueues ``LoopDeliverable`` only; **no wire imports**
- **Enqueue** — ``OutputQueue`` mirrors + ``persist_deliverable_transcript`` (same JSONL row; optional ``tool_results_digest``)
- **Delivery** — ``ChannelTurn`` starts ``deliver_output_queue`` → ``Channel.deliver`` (``Downlink`` projection in ``agentic_companion``)

## Three layers (agentic core view)

- **FromChannel** — existing uplink parsers + ``UplinkEnvelope`` + ``Session.run_user_turn`` (no new class)
- **ToChannel** — ``Channel`` ABC: ``deliver(Downlink)`` only
- **Turn boundary** — ``ChannelTurn.open`` creates ``OutputQueue``, runs delivery task, closes on exit

## Key types

- ``OutputQueue`` — async FIFO; enqueue-only (retired push-immediate ``channel.deliver``)
- ``DeliveryPolicy`` / ``TerminalReplyDelivery`` — bootstrap terminal ``USER_REPLY`` held until queue close
- ``ChannelTurn`` — per-turn queue + delivery lifecycle (platform-agnostic)
- ``CompanionRuntimeChannel`` — enum kind tag; ``Channel`` is the deliver object

## Outbound routing

- **Agentic loop (wired)** — queue → ``deliver_output_queue`` → ``Channel.deliver``
- **Inner-tick proactive** — ``Session.channel.deliver`` direct (legacy path; #3398)
- **Thread tool_bg** — ``Session.channel.deliver`` direct + inline transcript (legacy; #3398)

## Retired patches (wired agentic-loop path)

- ``AgenticLoopOutputQueue._push`` push-immediate deliver
- ``DownlinkLoopChannelAdapter`` / ``LoopChannelAdapter`` / ``LoopProjectionContext.defer_terminal_user_reply``
- ``agentic_loop_suppresses_transport_reply`` — wired IM returns ``""``; user-visible text only via ``Channel.deliver``
- Transport ``handle_user_text`` return → second ``sendMessage`` for same assistant text
- ``in_turn_sync_tool_loop`` inline interim transcript when wired interim sink is set (queue owns transcript)

## Tests

```bash
uv run pytest tests/app/core/companion_harness/loop/ \
  tests/app/services/agentic_companion/ \
  tests/app/services/agentic_channel/ -q
uv run python -m app.core.companion_harness.loop.parity.smoke compare-legacy --scenario tool_feedback
```

## Related

- #3398 — legacy REPL / thread tool_bg convergence
- #3402 — chunk sink / bootstrap interim retirement
