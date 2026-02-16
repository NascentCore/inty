"""
app.utils.audio 单元测试：PCM 重采样与单路拼接。

CREATED_BY_AGENT
"""

import struct

import pytest

from app.utils.audio import (
    build_interleaved_pcm_24k,
    resample_pcm_16k_to_24k,
)


def test_resample_pcm_16k_to_24k_empty():
    assert resample_pcm_16k_to_24k(b"") == b""
    assert resample_pcm_16k_to_24k(b"x") == b""


def test_resample_pcm_16k_to_24k_odd_length_returns_empty():
    assert resample_pcm_16k_to_24k(b"xxx") == b""


def test_resample_pcm_16k_to_24k_ratio():
    # 2 个 16-bit 采样 (4 bytes) -> 3 个采样 (6 bytes)，比例 2:3
    two_samples = struct.pack("<hh", 100, -200)
    out = resample_pcm_16k_to_24k(two_samples)
    assert len(out) == 6
    samples = struct.unpack("<hhh", out)
    assert samples[0] == 100
    assert samples[2] == -200
    assert -200 <= samples[1] <= 100


def test_resample_pcm_16k_to_24k_larger():
    num_in = 160  # 0.01 s at 16k
    pcm_in = struct.pack(f"<{num_in}h", *list(range(num_in)))
    out = resample_pcm_16k_to_24k(pcm_in)
    expected_out_samples = (24 * num_in + 15) // 16
    assert len(out) == expected_out_samples * 2


def test_build_interleaved_pcm_24k_empty():
    assert build_interleaved_pcm_24k([]) == b""


def test_build_interleaved_pcm_24k_user_only_16k():
    # 4 bytes user @ 16k -> resampled to 6 bytes @ 24k
    user_chunk = struct.pack("<hh", 1, 2)
    out = build_interleaved_pcm_24k(
        [("user", user_chunk)],
        user_sample_rate=16000,
        ai_sample_rate=24000,
    )
    assert len(out) == 6


def test_build_interleaved_pcm_24k_user_only_24k():
    # user @ 24k 不重采样，直接追加
    user_chunk = struct.pack("<hhh", 1, 2, 3)
    out = build_interleaved_pcm_24k(
        [("user", user_chunk)],
        user_sample_rate=24000,
        ai_sample_rate=24000,
    )
    assert out == user_chunk


def test_build_interleaved_pcm_24k_ai_only():
    ai_chunk = struct.pack("<hhh", 10, 20, 30)
    out = build_interleaved_pcm_24k(
        [("ai", ai_chunk)],
        user_sample_rate=16000,
        ai_sample_rate=24000,
    )
    assert out == ai_chunk


def test_build_interleaved_pcm_24k_interleaved():
    user_chunk = struct.pack("<hh", 1, 2)
    ai_chunk = struct.pack("<hh", 10, 20)
    out = build_interleaved_pcm_24k(
        [
            ("user", user_chunk),
            ("ai", ai_chunk),
        ],
        user_sample_rate=16000,
        ai_sample_rate=24000,
    )
    assert len(out) == 6 + 4
    ai_part = out[6:]
    assert ai_part == ai_chunk
