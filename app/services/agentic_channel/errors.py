"""Agent-channel endpoint binding errors."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError


class ChannelEndpointConflictError(ValueError):
    """Raised when bind would violate channel human ↔ Inty user 1:1 bonding."""


class CompanionBondInvariantError(ValueError):
    """Raised when active companion bond state is missing or ambiguous."""


def integrity_error_detail(exc: IntegrityError) -> str:
    """Summarize Postgres constraint info for Cloud Logging (INFO/WARNING sinks)."""
    orig = exc.orig
    if orig is None:
        return repr(exc)
    parts: list[str] = [str(orig)]
    pgcode = getattr(orig, "pgcode", None)
    if pgcode:
        parts.append(f"pgcode={pgcode}")
    diag = getattr(orig, "diag", None)
    if diag is not None:
        constraint = getattr(diag, "constraint_name", None)
        if constraint:
            parts.append(f"constraint={constraint}")
    return " ".join(parts)
