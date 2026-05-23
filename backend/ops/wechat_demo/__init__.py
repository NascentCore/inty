"""Ops-only WeChat self-service demo.

The demo lets an internal tester paste an Inty bearer token and agent id,
complete WeChat QR login, then relay WeChat direct messages into Inty's
WebSocket chat path. Sessions live only in the current Ops process and are
discarded on restart; this keeps the workflow safe for demos but unsuitable as
a durable messaging integration.
"""
