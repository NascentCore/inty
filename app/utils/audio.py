"""
音频工具：PCM 重采样等，供 live chat 单路 WAV 生成使用。

CREATED_BY_AGENT
"""

import math
import struct
from typing import List, Optional, Tuple

# Gemini Live 同一轮内多个 inline_data 分包接缝：用 cosine 淡化，略长于线性窗以减轻「AI 段内」碎裂感
AI_PART_CROSSFADE_SAMPLES = 224  # ~9.3ms @ 24kHz


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


def join_pcm_parts_24k_crossfade(
    parts: List[bytes],
    n_samples: int = AI_PART_CROSSFADE_SAMPLES,
) -> bytes:
    """
    将多段 24kHz 16-bit 单声道 PCM 顺序拼接，段与段之间 cosine 交叉淡化。

    针对 Gemini Live 多分包下行：减轻 AI 回复「段内」接缝爆音/碎裂，不做 user/AI 轨切换处理
    （整条会话仍由 build_interleaved_pcm_24k 按顺序拼接）。
    """
    nonempty = [bytes(p) for p in parts if p]
    if not nonempty:
        return b""
    if len(nonempty) == 1:
        return nonempty[0]
    out = bytearray(nonempty[0])
    nb = n_samples * 2
    denom = max(n_samples - 1, 1)
    for nxt in nonempty[1:]:
        if n_samples < 2 or len(out) < nb or len(nxt) < nb:
            out.extend(nxt)
            continue
        tail = struct.unpack_from(f"<{n_samples}h", out, len(out) - nb)
        head = struct.unpack_from(f"<{n_samples}h", nxt, 0)
        blended: List[int] = []
        for i in range(n_samples):
            a = (1.0 - math.cos(math.pi * i / denom)) / 2.0
            v = int(tail[i] * (1.0 - a) + head[i] * a)
            blended.append(max(-32768, min(32767, v)))
        out[len(out) - nb :] = struct.pack(f"<{n_samples}h", *blended)
        out.extend(nxt[nb:])
    return bytes(out)


def build_interleaved_pcm_24k(
    conversation_chunks: List[Tuple[str, bytes]],
    *,
    user_sample_rate: int = 16000,
    ai_sample_rate: int = 24000,
) -> bytes:
    """
    按 conversation_chunks 顺序（用户–AI–用户–AI…）拼接为一段 24k、16-bit 单声道 PCM。

    - 连续 user 块先合并再一次性 16k→24k，避免分包重采样接缝失真。
    - 连续 AI 多块经 join_pcm_parts_24k_crossfade 再接上，减轻模型多分包在 AI 段内的爆音。
    """
    out = bytearray()
    pending_role: Optional[str] = None
    pending_user = bytearray()
    pending_ai_parts: List[bytes] = []

    def _flush_pending() -> None:
        nonlocal pending_role
        if pending_role is None:
            return
        pr = pending_role
        pending_role = None
        if pr == "user":
            blob16 = bytes(pending_user)
            pending_user.clear()
            if not blob16:
                return
            if user_sample_rate == 24000:
                seg = blob16
            elif user_sample_rate == 16000:
                seg = resample_pcm_16k_to_24k(blob16)
            else:
                seg = blob16
            out.extend(seg)
        else:
            parts = pending_ai_parts[:]
            pending_ai_parts.clear()
            if not parts:
                return
            seg = join_pcm_parts_24k_crossfade(parts, AI_PART_CROSSFADE_SAMPLES)
            out.extend(seg)

    for role, data in conversation_chunks:
        if not data:
            continue
        if pending_role is not None and role != pending_role:
            _flush_pending()
        if pending_role is None:
            pending_role = role
        if role == "user":
            pending_user.extend(data)
        else:
            pending_ai_parts.append(bytes(data))

    _flush_pending()
    return bytes(out)
