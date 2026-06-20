"""Unit tests for iLink session-expired detection helpers."""

from __future__ import annotations

import pytest

from backend.ops.weixin_channel.ilink_qr_client import (
    ILINK_RATE_LIMIT_ERRCODE,
    ILINK_SESSION_EXPIRED_ERRCODE,
    is_ilink_session_expired,
    is_ilink_session_expired_runtime_error,
)


def test_is_ilink_session_expired_errcode_minus_14() -> None:
    assert is_ilink_session_expired(None, ILINK_SESSION_EXPIRED_ERRCODE, None)
    assert is_ilink_session_expired(ILINK_SESSION_EXPIRED_ERRCODE, None, None)


def test_is_ilink_session_expired_stale_unknown_error() -> None:
    assert is_ilink_session_expired(
        ILINK_RATE_LIMIT_ERRCODE,
        None,
        "unknown error",
    )
    assert is_ilink_session_expired(
        None,
        ILINK_RATE_LIMIT_ERRCODE,
        "Unknown Error",
    )


def test_is_ilink_session_expired_rejects_rate_limit_without_unknown_error() -> (
    None
):
    assert not is_ilink_session_expired(
        ILINK_RATE_LIMIT_ERRCODE,
        ILINK_RATE_LIMIT_ERRCODE,
        "too frequent",
    )


def test_is_ilink_session_expired_runtime_error_parses_hermes_message() -> None:
    exc = RuntimeError(
        "iLink sendmessage error: ret=-14 errcode=-14 errmsg=session expired"
    )
    assert is_ilink_session_expired_runtime_error(exc)


def test_is_ilink_session_expired_runtime_error_rejects_other() -> None:
    assert not is_ilink_session_expired_runtime_error(
        RuntimeError("iLink sendmessage error: ret=0 errcode=1 errmsg=fail")
    )
    assert not is_ilink_session_expired_runtime_error(ValueError("errcode=-14"))
