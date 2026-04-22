"""
生成语音测试用例音频文件

使用 edge-tts 生成中英文测试音频，输出 16kHz 16bit mono PCM WAV，
匹配 inty-backend 服务端 send_sample_rate=16000。

Usage:
    python generate_test_audio.py          # 生成所有测试音频
    python generate_test_audio.py --list   # 列出测试用例
"""

import argparse
import asyncio
import io
import struct
import subprocess
import sys
import wave
from pathlib import Path

TEST_AUDIO_DIR = Path(__file__).resolve().parent / "test_audio"

# ==== 测试用例定义 ====
# (文件名, 文本, 音色, 描述, 是否插入静音)
TEST_CASES = [
    # --- 问题1: 语言混用 ---
    (
        "cn_short",
        "你好，今天天气怎么样？",
        "zh-CN-XiaoxiaoNeural",
        "短中文问候",
        False,
    ),
    (
        "en_short",
        "What's the weather like today?",
        "en-US-JennyNeural",
        "短英文问候",
        False,
    ),
    (
        "cn_mixed",
        "我想了解一下machine learning的最新应用和发展趋势。",
        "zh-CN-XiaoxiaoNeural",
        "中英混合句子",
        False,
    ),
    (
        "en_mixed",
        "Can you explain 人工智能 in simple terms?",
        "en-US-JennyNeural",
        "英中混合句子",
        False,
    ),
    # --- 问题2: 长句截断 ---
    (
        "cn_long",
        (
            "今天我想跟你详细聊一聊关于人工智能的发展历程，"
            "从最早的图灵测试开始，到后来的专家系统，"
            "再到现在的深度神经网络和大语言模型，"
            "这个领域经历了非常多的变化和技术突破，"
            "每一次进步都推动了人类社会的巨大变革。"
        ),
        "zh-CN-YunxiNeural",
        "中文长句(自然停顿)",
        False,
    ),
    (
        "en_long",
        (
            "I'd like to talk about the history of artificial intelligence in detail, "
            "starting from the early Turing test, moving through expert systems, "
            "and arriving at today's deep neural networks and large language models, "
            "this field has undergone tremendous changes and technological breakthroughs, "
            "each advancement driving significant transformation in human society."
        ),
        "en-US-JennyNeural",
        "英文长句(自然停顿)",
        False,
    ),
    (
        "cn_long_pause",
        ("今天我想跟你详细聊一聊关于人工智能的发展历程，"),
        "zh-CN-YunxiNeural",
        "中文长句+人工静音段(触发VAD截断)",
        True,  # 将在 TTS 后插入 600ms 静音
    ),
    (
        "en_long_pause",
        ("I'd like to talk about the history of artificial intelligence in detail, "),
        "en-US-JennyNeural",
        "英文长句+人工静音段(触发VAD截断)",
        True,
    ),
    # --- 连续多轮测试(语言切换) ---
    (
        "cn_turn1",
        "你好，我想练习英语口语。",
        "zh-CN-XiaoxiaoNeural",
        "中文第1轮",
        False,
    ),
    (
        "en_turn2",
        "Can you help me practice English speaking?",
        "en-US-JennyNeural",
        "英文第2轮(切换语言)",
        False,
    ),
    (
        "cn_turn3",
        "好的，那我们用中文聊吧。",
        "zh-CN-XiaoxiaoNeural",
        "中文第3轮(切回)",
        False,
    ),
]

SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2  # 16-bit
CHANNELS = 1


def _check_edge_tts():
    """检查 edge-tts 是否可用"""
    try:
        subprocess.run(
            [sys.executable, "-m", "edge_tts", "--version"],
            capture_output=True,
            timeout=10,
        )
        return True
    except Exception:
        return False


def _install_edge_tts():
    print("edge-tts 未安装，正在安装...")
    subprocess.run([sys.executable, "-m", "pip", "install", "edge-tts"], check=True)


async def _tts(text: str, voice: str, output_path: Path) -> None:
    """使用 edge-tts 生成音频"""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    audio_data = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.extend(chunk["data"])
    output_path.write_bytes(bytes(audio_data))


def _convert_mp3_to_wav(mp3_path: Path, wav_path: Path) -> None:
    """将 MP3 转换为 16kHz 16bit mono WAV"""
    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_mp3(str(mp3_path))
        audio = (
            audio.set_frame_rate(SAMPLE_RATE)
            .set_channels(CHANNELS)
            .set_sample_width(SAMPLE_WIDTH)
        )
        audio.export(str(wav_path), format="wav")
    except ImportError:
        # fallback: 使用 ffmpeg
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(mp3_path),
                "-ar",
                str(SAMPLE_RATE),
                "-ac",
                str(CHANNELS),
                "-sample_fmt",
                "s16",
                str(wav_path),
            ],
            capture_output=True,
            check=True,
        )


def _insert_silence(wav_path: Path, silence_ms: int = 600) -> bytes:
    """在 WAV 音频末尾插入静音段"""
    with wave.open(str(wav_path), "rb") as wf:
        params = wf.getparams()
        frames = wf.readframes(wf.getnframes())

    silence_samples = int(SAMPLE_RATE * silence_ms / 1000)
    silence_bytes = b"\x00\x00" * silence_samples

    return frames + silence_bytes


def _write_pcm_wav(path: Path, pcm_data: bytes) -> None:
    """将原始 PCM 数据写入 WAV 文件"""
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_data)


def _get_pcm_from_wav(wav_path: Path) -> bytes:
    """从 WAV 文件读取 PCM 数据"""
    with wave.open(str(wav_path), "rb") as wf:
        return wf.readframes(wf.getnframes())


async def generate_all():
    """生成所有测试音频"""
    if not _check_edge_tts():
        _install_edge_tts()

    TEST_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    for name, text, voice, desc, add_silence in TEST_CASES:
        wav_path = TEST_AUDIO_DIR / f"{name}.wav"
        mp3_tmp = TEST_AUDIO_DIR / f"{name}.mp3"

        print(f"生成: {name}.wav ({desc})")
        try:
            await _tts(text, voice, mp3_tmp)
            _convert_mp3_to_wav(mp3_tmp, wav_path)

            if add_silence:
                pcm_with_silence = _insert_silence(wav_path, silence_ms=600)
                _write_pcm_wav(wav_path, pcm_with_silence)
                print(f"  -> 已插入 600ms 静音段")

            # 清理临时 mp3
            mp3_tmp.unlink(missing_ok=True)

            # 打印音频信息
            pcm = _get_pcm_from_wav(wav_path)
            duration_ms = len(pcm) / (SAMPLE_RATE * SAMPLE_WIDTH) * 1000
            print(
                f"  -> {len(pcm)} bytes, {duration_ms:.0f}ms, {SAMPLE_RATE}Hz mono 16bit"
            )
        except Exception as e:
            print(f"  -> 失败: {e}")


def list_cases():
    """列出所有测试用例"""
    print(f"{'文件名':<20} {'描述':<40}")
    print("-" * 60)
    for name, text, voice, desc, add_silence in TEST_CASES:
        print(f"{name + '.wav':<20} {desc:<40}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成语音测试用例音频")
    parser.add_argument("--list", action="store_true", help="列出所有测试用例")
    args = parser.parse_args()

    if args.list:
        list_cases()
    else:
        asyncio.run(generate_all())
        print("\n所有测试音频已生成到:", TEST_AUDIO_DIR)
