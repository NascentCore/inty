"""Shim: Fal z-image tool implementation lives in companion.fal_z_image_tool."""

from __future__ import annotations

from app.core.agentic_kernel.companion.fal_z_image_tool import (
    MAX_NUM_IMAGES_PER_CALL,
    reset_fal_async_client_after_short_lived_loop,
    run_generate_image_z_image_turbo,
    run_modify_image_z_image_turbo,
)

_reset_fal_async_client_after_short_lived_loop = reset_fal_async_client_after_short_lived_loop
