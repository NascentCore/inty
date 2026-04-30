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


def test_resample_pcm_16k_to_24k_odd_length_truncates_last_byte():
    # 奇数字节：丢弃末尾 1 字节后按偶数帧重采样，避免整段被丢弃
    three_bytes = struct.pack("<h", 900) + b"\x00"
    out = resample_pcm_16k_to_24k(three_bytes)
    assert out == resample_pcm_16k_to_24k(struct.pack("<h", 900))


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


def test_build_interleaved_pcm_24k_merges_consecutive_user_before_resample():
    c1 = struct.pack("<hh", 1000, 2000)
    c2 = struct.pack("<hh", 3000, 4000)
    out = build_interleaved_pcm_24k(
        [("user", c1), ("user", c2)],
        user_sample_rate=16000,
        ai_sample_rate=24000,
    )
    assert out == resample_pcm_16k_to_24k(c1 + c2)


def test_build_interleaved_pcm_24k_merges_consecutive_ai():
    a1 = struct.pack("<h", 11)
    a2 = struct.pack("<hhh", 22, 33, 44)
    out = build_interleaved_pcm_24k(
        [("ai", a1), ("ai", a2)],
        user_sample_rate=16000,
        ai_sample_rate=24000,
    )
    assert out == a1 + a2
