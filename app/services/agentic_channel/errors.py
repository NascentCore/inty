"""Agent-channel endpoint binding errors."""

from __future__ import annotations


class ChannelEndpointConflictError(ValueError):
    """Raised when bind would violate channel human ↔ Inty user 1:1 bonding."""
