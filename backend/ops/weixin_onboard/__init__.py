"""Weixin scan onboard: provision Inty user + agent after iLink QR confirm.

MVP stores ``ilink_user_id`` in ``users.meta_data`` (``AuthType.GUEST``).

Follow-up TODOs:
- ``weixin-onboard-auth-type``: ``AuthType.WEIXIN`` + dedicated column + index
- ``weixin-onboard-agent-policy``: agent template from config
- ``weixin-onboard-jwt-delivery``: one-time code or WeChat DM (JWT never on poll)
"""
