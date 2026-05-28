"""WeChat ↔ Inty self-service demo (Ops only; bridge state in Postgres).

iLink session limits: QR poll budget 480s; each QR may ``expired`` (≤3 refresh).
Bridge ``weixin_token`` lasts until iLink ``errcode=-14`` (negative fourteen — not
14-minute QR validity). Then Stop + Start QR Login again.

WeChat chatter presence (opened WeChat / opened bot chat) is **not** detectable via
iLink; only inbound DMs update ``last_peer_seen_at`` (see ``backend.ops.weixin_channel``).

Release smoke (bridge persist + Ops restart restore):
``.cursor/skills/wechat-demo-bridge-restore-smoke/SKILL.md``.

TODO(wechat-demo-bridge-multi-replica): single Ops runner required; multiple Pods restore
all bridge rows and duplicate Weixin connections.

TODO(wechat-demo-ws-disconnect-hermes-wording): if only Inty backend restarts while Ops
bridge stays up, companion WS dies (1012) until Ops restart/restore or demo stop/start;
WeChat users may see Hermes "use /reset"—see ``backend.ops.weixin_channel``.
But Inty does not have /reset command. This could be confusing.
"""
