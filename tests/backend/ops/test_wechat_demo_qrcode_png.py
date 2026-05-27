"""Tests for local WeChat demo QR PNG generation."""

from __future__ import annotations

from backend.ops.wechat_demo.qrcode_png import (
    WECHAT_DEMO_QR_BOX_SIZE,
    qrcode_png_bytes,
)


def test_qrcode_png_bytes_returns_png_magic() -> None:
    png = qrcode_png_bytes("wechat-demo-payload", WECHAT_DEMO_QR_BOX_SIZE)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
