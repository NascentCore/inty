"""In-process companion presence lease: one WS holder per ``(user_id, agent_id)``.

MVP rejects a second WebSocket ``user_signed_on`` for the same scope; incumbent
connection keeps its lease until ``user_signed_out`` or disconnect ``release``.

Deferred work (not in MVP):

- ``TODO(companion-presence-chat-gate)`` — ``holds()`` before chat turn for clients
  without ``user_signed_on``.
- ``TODO(companion-presence-weixin)`` — Weixin ``try_register`` / cross-channel.
- ``TODO(companion-presence-lease-distributed)`` — multi-process / Redis lease.
- ``TODO(companion-presence-switching)`` — user-initiated channel switch UX.
- ``TODO(companion-ws-query-agent-id-at-connect)`` — accept-time agent bind (#3272).
"""

from __future__ import annotations

from dataclasses import dataclass, field


class PresenceBusyError(Exception):
    """Another holder already owns the ``(user_id, agent_id)`` lease."""

    def __init__(
        self,
        lease_key: str,
        incumbent_holder_id: str,
        requested_holder_id: str,
    ) -> None:
        self.lease_key = lease_key
        self.incumbent_holder_id = incumbent_holder_id
        self.requested_holder_id = requested_holder_id
        super().__init__(
            f"presence busy key={lease_key} incumbent={incumbent_holder_id} "
            f"requested={requested_holder_id}"
        )


@dataclass
class _PresenceLease:
    holder_id: str


@dataclass
class CompanionPresenceRegistry:
    """Process-wide registry mapping scope keys to a single live holder id."""

    _leases: dict[str, _PresenceLease] = field(default_factory=dict)

    @staticmethod
    def _lease_key(user_id: str, agent_id: str) -> str:
        uid = user_id.strip()
        aid = agent_id.strip()
        assert uid
        assert aid
        return f"{uid}:{aid}"

    def try_register(
        self,
        user_id: str,
        agent_id: str,
        holder_id: str,
    ) -> None:
        """Claim ``(user_id, agent_id)`` for ``holder_id``; raise if another holder owns it."""
        hid = holder_id.strip()
        assert hid
        key = self._lease_key(user_id, agent_id)
        existing = self._leases.get(key)
        if existing is not None and existing.holder_id != hid:
            raise PresenceBusyError(key, existing.holder_id, hid)
        self._leases[key] = _PresenceLease(holder_id=hid)

    def release(
        self,
        user_id: str,
        agent_id: str,
        holder_id: str,
    ) -> None:
        """Drop the lease when ``holder_id`` matches; no-op otherwise."""
        hid = holder_id.strip()
        assert hid
        key = self._lease_key(user_id, agent_id)
        existing = self._leases.get(key)
        if existing is None or existing.holder_id != hid:
            return
        del self._leases[key]


_process_registry = CompanionPresenceRegistry()


def companion_presence_registry() -> CompanionPresenceRegistry:
    """Return the process-wide companion presence registry."""
    return _process_registry
