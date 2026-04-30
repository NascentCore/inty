"""
音频工具：PCM 重采样等，供 live chat 单路 WAV 生成使用。

CREATED_BY_AGENT
"""

import math
import struct
from typing import List, Optional, Tuple

# Gemini Live 同一轮内多个 inline_data 分包接缝：先裁掉分包之间常见的尾/头近静音垫，再 cosine 淡化
AI_PART_CROSSFADE_SAMPLES = 224  # ~9.3ms @ 24kHz
# |sample| < gate 视为静音；仅裁分包边界，单段最多裁若干 ms，避免吃掉句内刻意停顿
_AI_EDGE_SILENCE_GATE = 384
_AI_TRIM_TRAIL_MS = 420.0
_AI_TRIM_LEAD_MS = 220.0
# 过短分包不做边界裁剪（避免误伤小包/单元测试样例）
_AI_MIN_SAMPLES_FOR_EDGE_TRIM = 240  # 10ms @ 24kHz
_USER_INTER_AI_SILENCE_GATE = 384
_USER_INTER_AI_MAX_LOUD_RATIO = 0.01


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


def _trim_leading_near_silence_pcm16_mono(
    pcm: bytes,
    *,
    sample_rate: int,
    max_trim_ms: float,
    gate: int,
) -> bytes:
    if len(pcm) < 4 or len(pcm) % 2 != 0:
        return pcm
    ns = len(pcm) // 2
    if ns < _AI_MIN_SAMPLES_FOR_EDGE_TRIM:
        return pcm
    samples = struct.unpack("<%dh" % ns, pcm)
    max_sil = int(sample_rate * (max_trim_ms / 1000.0))
    if max_sil < 1:
        return pcm
    t = 0
    sil = 0
    while t < ns and abs(samples[t]) < gate and sil < max_sil:
        t += 1
        sil += 1
    if t == 0:
        return pcm
    new_ns = ns - t
    if new_ns < 1:
        return b""
    return struct.pack("<%dh" % new_ns, *samples[t:])


def _trim_trailing_near_silence_pcm16_mono(
    pcm: bytes,
    *,
    sample_rate: int,
    max_trim_ms: float,
    gate: int,
) -> bytes:
    if len(pcm) < 4 or len(pcm) % 2 != 0:
        return pcm
    ns = len(pcm) // 2
    if ns < _AI_MIN_SAMPLES_FOR_EDGE_TRIM:
        return pcm
    samples = struct.unpack("<%dh" % ns, pcm)
    max_sil = int(sample_rate * (max_trim_ms / 1000.0))
    if max_sil < 1:
        return pcm
    t = ns - 1
    sil = 0
    while t >= 0 and abs(samples[t]) < gate and sil < max_sil:
        t -= 1
        sil += 1
    new_ns = t + 1
    if new_ns < 1:
        return b""
    if new_ns == ns:
        return pcm
    return struct.pack("<%dh" % new_ns, *samples[:new_ns])


def _preprocess_gemini_ai_parts_edges(
    parts: List[bytes],
    *,
    sample_rate: int = 24000,
) -> List[bytes]:
    """
    去掉相邻 AI 分包之间常见的尾/头近静音（Gemini 分包间易出现数百 ms 低电平），
    再交给 cosine 淡化接缝；不处理单段内部的句中停顿（中间段尾部最多裁 _AI_TRIM_TRAIL_MS）。
    """
    nonempty = [bytes(p) for p in parts if p]
    if len(nonempty) <= 1:
        return nonempty
    out: List[bytes] = []
    for i, p in enumerate(nonempty):
        q = p
        if i > 0:
            q = _trim_leading_near_silence_pcm16_mono(
                q,
                sample_rate=sample_rate,
                max_trim_ms=_AI_TRIM_LEAD_MS,
                gate=_AI_EDGE_SILENCE_GATE,
            )
        if i < len(nonempty) - 1:
            q = _trim_trailing_near_silence_pcm16_mono(
                q,
                sample_rate=sample_rate,
                max_trim_ms=_AI_TRIM_TRAIL_MS,
                gate=_AI_EDGE_SILENCE_GATE,
            )
        if len(q) >= 2:
            out.append(q)
    return out if out else nonempty


def _is_near_silence_pcm16_mono(
    pcm: bytes,
    *,
    gate: int,
    max_loud_ratio: float,
) -> bool:
    if not pcm or len(pcm) % 2 != 0:
        return False
    ns = len(pcm) // 2
    samples = struct.unpack("<%dh" % ns, pcm)
    loud = sum(1 for sample in samples if abs(sample) >= gate)
    return (loud / ns) <= max_loud_ratio


def _drop_user_near_silence_between_ai(
    conversation_chunks: List[Tuple[str, bytes]],
) -> List[Tuple[str, bytes]]:
    """
    保存单路 WAV 时，客户端在 AI 回复期间仍可能上传麦克风静音。
    如果这类 user 近静音刚好夹在两个 AI 分包之间，丢掉它以保持 AI 回复连续。
    """
    nonempty = [(role, data) for role, data in conversation_chunks if data]
    if len(nonempty) < 3:
        return nonempty

    out: List[Tuple[str, bytes]] = []
    idx = 0
    while idx < len(nonempty):
        role, data = nonempty[idx]
        if role != "user":
            out.append((role, data))
            idx += 1
            continue

        run_start = idx
        run: List[Tuple[str, bytes]] = []
        while idx < len(nonempty) and nonempty[idx][0] == "user":
            run.append(nonempty[idx])
            idx += 1
        prev_role = nonempty[run_start - 1][0] if run_start > 0 else None
        next_role = nonempty[idx][0] if idx < len(nonempty) else None
        if (
            prev_role != "user"
            and next_role != "user"
            and all(
                _is_near_silence_pcm16_mono(
                    chunk_data,
                    gate=_USER_INTER_AI_SILENCE_GATE,
                    max_loud_ratio=_USER_INTER_AI_MAX_LOUD_RATIO,
                )
                for _, chunk_data in run
            )
        ):
            continue
        out.extend(run)
    return out


def join_pcm_parts_24k_crossfade(
    parts: List[bytes],
    n_samples: int = AI_PART_CROSSFADE_SAMPLES,
) -> bytes:
    """
    将多段 24kHz 16-bit 单声道 PCM 顺序拼接，段与段之间 cosine 交叉淡化。

    针对 Gemini Live 多分包下行：减轻 AI 回复「段内」接缝爆音/碎裂，不做 user/AI 轨切换处理
    （整条会话仍由 build_interleaved_pcm_24k 按顺序拼接）。
    """
    nonempty = _preprocess_gemini_ai_parts_edges(
        [bytes(p) for p in parts if p],
        sample_rate=24000,
    )
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

    for role, data in _drop_user_near_silence_between_ai(conversation_chunks):
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
