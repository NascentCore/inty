# Companion

Memory processing pipeline. Abstract **coherent scope state** and **behavior display**
(text / image / voice-audio). Production user entry: **WebSocket + Weixin only**; HTTP
chat not planned unless explicitly requested.

## LLM invocation tracks

- User chat: respond to user message
- Greeting: proactive greeting message when detected user signed on
- Proactive chat: proactive messages sent to user when user is not sending any message
- Scheduled activity: activities that are scheduled to be fired in the future
- Maintenance: regular maintenance, background & hidden from users, to process & reorganize the chat messages.
  - TODO(inner-tick-autonomy): Replace with **Autonomy** — idle inner-tick only advances ``ai_private.jsonl`` (model-hallucinated intrinsic beats); profile/MemoryDoc consistency belongs in **dreaming**; rename track/activity/scheduling after scope cut (see ``models.InnerTickActivity``).
