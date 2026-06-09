"""Weixin onboard sessions: in-memory registry + Postgres-backed bridge resume (Ops only).

iLink limits: QR phase — ``WeixinQrFlow`` + ``WEIXIN_QR_LOGIN_POLL_TIMEOUT_SECONDS``
(480s). Onboard: ``expired`` fails (F5 for new QR); POST blocks on
``WEIXIN_ONBOARD_QR_READY_TIMEOUT_SECONDS``. Bridge phase — ``weixin_token`` until iLink
``errcode=-14`` (re QR).

Release smoke (bridge persist + Ops restart restore):
``.cursor/skills/weixin-bridge-restore-smoke/SKILL.md``.

TODO(weixin-bridge-multi-replica): single Ops runner required; multiple Pods restore
all bridge rows and duplicate Weixin connections.

TODO(weixin-ws-disconnect-hermes-wording): if only Inty backend restarts while Ops
bridge stays up, companion path may stall until Ops restart/restore or session stop/start;
see ``backend.ops.weixin_channel``.
"""
