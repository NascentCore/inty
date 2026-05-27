"""Render WeChat demo QR login payload as PNG (local ``qrcode`` PyPI package)."""

from __future__ import annotations

import io

import qrcode
from qrcode.constants import ERROR_CORRECT_M

# Matches prior qrserver.com 240x240 display (~10px modules + border).
WECHAT_DEMO_QR_BOX_SIZE = 10


def qrcode_png_bytes(payload: str, box_size: int) -> bytes:
    """Encode ``payload`` as a PNG QR image."""
    assert payload != ""
    assert box_size > 0
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=box_size,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
