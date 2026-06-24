"""SMS session store scope cache."""

from __future__ import annotations

from app.core.companion_harness.agent_channel.scope import AgentScope
from backend.ops.sms_channel import session_store


def test_get_scope_for_user_phone() -> None:
    session_store.clear_all_for_tests()
    scope = AgentScope(user_id="user-1", agent_id="agent-1")
    session_store.remember_scope(user_phone_e164="+11234560123", scope=scope)
    assert session_store.get_scope_for_user_phone("+11234560123") == scope
    session_store.forget_scope(user_phone_e164="+11234560123")
    assert session_store.get_scope_for_user_phone("+11234560123") is None
