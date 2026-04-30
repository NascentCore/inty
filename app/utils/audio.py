"""
音频工具：PCM 重采样等，供 live chat 单路 WAV 生成使用。

CREATED_BY_AGENT
"""

import struct
from typing import List, Optional, Tuple


def resample_pcm_16k_to_24k(pcm_bytes: bytes) -> bytes:
    """
    将 16-bit 单声道 PCM 从 16 kHz 重采样到 24 kHz（线性插值）。

    比例 16:24 = 2:3，即每 2 个输入采样产生 3 个输出采样。
    """
    if not pcm_bytes:
        return b""
    if len(pcm_bytes) % 2 != 0:
        pcm_bytes = pcm_bytes[:-1]
    if not pcm_bytes:
        return b""
    num_in = len(pcm_bytes) // 2
    # 24/16 * num_in 个输出采样，每采样 2 字节
    num_out = (24 * num_in + 15) // 16
    out_list: List[int] = []
    for i in range(num_out):
        src_idx = i * 16 / 24
        i0 = int(src_idx)
        i1 = min(i0 + 1, num_in - 1)
        frac = src_idx - i0
        s0 = struct.unpack_from("<h", pcm_bytes, i0 * 2)[0]
        s1 = struct.unpack_from("<h", pcm_bytes, i1 * 2)[0]
        sample = int(s0 + frac * (s1 - s0))
        sample = max(-32768, min(32767, sample))
        out_list.append(sample)
    return struct.pack(f"<{len(out_list)}h", *out_list)


def build_interleaved_pcm_24k(
    conversation_chunks: List[Tuple[str, bytes]],
    *,
    user_sample_rate: int = 16000,
    ai_sample_rate: int = 24000,
) -> bytes:
    """
    按 conversation_chunks 顺序（用户–AI–用户–AI…）拼接为一段 24k、16-bit 单声道 PCM。

    先将**连续同 role** 的多个小块合并后再处理，避免对 16k 用户轨「分包重采样」
    在包边界产生相位不连续与可听爆音/碎裂感。

    - ("user", data): 视为 user_sample_rate（默认 16k），重采样到 24k 后追加。
    - 其他 role（如 "ai"）: 视为 ai_sample_rate（默认 24k），直接追加。
    """
    out = bytearray()
    pending_role: Optional[str] = None
    pending = bytearray()

    def _flush_pending() -> None:
        nonlocal pending_role, pending
        if pending_role is None:
            return
        blob = bytes(pending)
        pending.clear()
        pr = pending_role
        pending_role = None
        if not blob:
            return
        if pr == "user":
            if user_sample_rate == 24000:
                out.extend(blob)
            elif user_sample_rate == 16000:
                out.extend(resample_pcm_16k_to_24k(blob))
            else:
                out.extend(blob)
        else:
            out.extend(blob)

    for role, data in conversation_chunks:
        if not data:
            continue
        if pending_role is not None and role != pending_role:
            _flush_pending()
        if pending_role is None:
            pending_role = role
        pending.extend(data)

    _flush_pending()
    return bytes(out)
