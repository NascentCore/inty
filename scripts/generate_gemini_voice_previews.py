#!/usr/bin/env python3
"""
生成 Gemini TTS 预置音色的预览音频并上传到 GCS

用法:
    python scripts/generate_gemini_voice_previews.py [--dry-run] [--voice VOICE_ID]

示例:
    # 生成所有音色的预览（dry-run 模式，不实际上传）
    python scripts/generate_gemini_voice_previews.py --dry-run

    # 生成所有音色的预览并上传
    python scripts/generate_gemini_voice_previews.py

    # 只生成指定音色的预览
    python scripts/generate_gemini_voice_previews.py --voice Zephyr

CREATED_BY_AGENT
"""

import asyncio
import sys
from pathlib import Path
from typing import Annotated, Optional

import cyclopts
import loguru

# 设置日志
logger = loguru.logger

# GCS 路径常量
GCS_VOICE_PREVIEW_BASE_PATH = "voice_previews/gemini"
PREVIEW_TEXT = "Hello, I'm your AI companion. Nice to meet you!"


async def generate_preview_for_voice(
    voice_id: str,
    bucket_name: str,
    dry_run: bool = False,
) -> Optional[str]:
    """
    为指定音色生成预览音频并上传到 GCS

    Args:
        voice_id: 音色 ID（如 "Zephyr"）
        bucket_name: GCS bucket 名称
        dry_run: 如果为 True，只打印日志不实际执行

    Returns:
        上传后的公开 URL，失败返回 None
    """
    from app.core.voice.tts_api import (
        DEFAULT_GEMINI_TTS_MODEL,
        GeminiTTSAPI,
        TTSRequest,
    )

    logger.info(f"正在为音色 '{voice_id}' 生成预览音频...")

    if dry_run:
        gcs_path = f"{GCS_VOICE_PREVIEW_BASE_PATH}/{voice_id}.mp3"
        preview_url = f"https://storage.googleapis.com/{bucket_name}/{gcs_path}"
        logger.info(f"[DRY-RUN] 将上传到: {preview_url}")
        return preview_url

    # 初始化 Gemini TTS API
    tts_api = GeminiTTSAPI()

    # 创建 TTS 请求（Gemini TTS 不使用 model_id 和 output_format，但 dataclass 需要）
    request = TTSRequest(
        text=PREVIEW_TEXT,
        voice_id=voice_id,
        model_id=DEFAULT_GEMINI_TTS_MODEL,
        output_format="mp3_44100_128",  # 仅用于满足 dataclass 要求
    )

    # 调用 Gemini TTS 生成音频
    result = await tts_api.synthesize(request)
    if result is None:
        logger.error(f"音色 '{voice_id}' TTS 生成失败")
        return None

    logger.info(
        f"音色 '{voice_id}' TTS 生成成功，"
        f"音频大小: {len(result.audio_bytes)} bytes, "
        f"格式: {result.mime_type}"
    )

    # 转换为 MP3 格式（如果是 WAV）
    audio_bytes = result.audio_bytes
    content_type = "audio/mpeg"

    if result.mime_type == "audio/wav":
        # 使用 pydub 转换 WAV 到 MP3
        try:
            from io import BytesIO

            from pydub import AudioSegment

            wav_io = BytesIO(result.audio_bytes)
            audio_segment = AudioSegment.from_wav(wav_io)

            mp3_io = BytesIO()
            audio_segment.export(mp3_io, format="mp3", bitrate="128k")
            audio_bytes = mp3_io.getvalue()

            logger.info(
                f"音色 '{voice_id}' WAV 转 MP3 成功，"
                f"转换后大小: {len(audio_bytes)} bytes"
            )
        except Exception as e:
            logger.warning(f"WAV 转 MP3 失败: {e}，将直接上传 WAV 格式")
            content_type = "audio/wav"

    # 确定文件扩展名
    file_ext = "mp3" if content_type == "audio/mpeg" else "wav"
    gcs_path = f"{GCS_VOICE_PREVIEW_BASE_PATH}/{voice_id}.{file_ext}"

    # 上传到 GCS
    from app.external_services.gcs import upload_to_gcs

    try:
        public_url = upload_to_gcs(
            file_data=audio_bytes,
            content_type=content_type,
            bucket_name=bucket_name,
            path=gcs_path,
        )
        logger.info(f"音色 '{voice_id}' 预览音频已上传: {public_url}")
        return public_url
    except Exception as e:
        logger.error(f"音色 '{voice_id}' 上传 GCS 失败: {e}")
        return None


async def generate_all_previews(
    dry_run: bool = False,
    voice_filter: Optional[str] = None,
) -> dict[str, Optional[str]]:
    """
    为所有 Gemini 预置音色生成预览音频

    Args:
        dry_run: 如果为 True，只打印日志不实际执行
        voice_filter: 只生成指定音色（用于测试）

    Returns:
        字典：voice_id -> preview_url（失败为 None）
    """
    from app.core.config import global_config_loaded_from_config_yaml
    from app.core.voice.tts_api import GEMINI_PREBUILT_VOICES

    bucket_name = global_config_loaded_from_config_yaml.gcs.bucket
    logger.info(f"GCS Bucket: {bucket_name}")

    # 过滤音色列表
    voices = GEMINI_PREBUILT_VOICES
    if voice_filter:
        voices = [v for v in voices if v["voice_id"] == voice_filter]
        if not voices:
            logger.error(f"未找到音色: {voice_filter}")
            return {}

    logger.info(f"将为 {len(voices)} 个音色生成预览音频")
    logger.info(f'预览文本: "{PREVIEW_TEXT}"')

    results: dict[str, Optional[str]] = {}

    for voice in voices:
        voice_id = voice["voice_id"]
        preview_url = await generate_preview_for_voice(
            voice_id=voice_id,
            bucket_name=bucket_name,
            dry_run=dry_run,
        )
        results[voice_id] = preview_url

        # 避免触发速率限制
        if not dry_run:
            await asyncio.sleep(1)

    # 打印汇总
    success_count = sum(1 for url in results.values() if url is not None)
    logger.info(f"生成完成: 成功 {success_count}/{len(results)}")

    if success_count > 0:
        logger.info("生成的 preview_url 列表（可用于更新 GEMINI_PREBUILT_VOICES）:")
        for voice_id, url in results.items():
            if url:
                logger.info(f'    "{voice_id}": "{url}",')

    return results


def main(
    dry_run: Annotated[
        bool,
        cyclopts.Parameter(
            name="--dry-run",
            help="只打印日志，不实际生成和上传",
        ),
    ] = False,
    voice: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--voice",
            help="只生成指定音色的预览（用于测试）",
        ),
    ] = None,
):
    """
    为 Gemini TTS 预置音色生成预览音频并上传到 GCS
    """
    logger.info("=" * 60)
    logger.info("Gemini TTS 音色预览生成工具")
    logger.info("=" * 60)

    if dry_run:
        logger.warning("DRY-RUN 模式：不会实际生成和上传文件")

    asyncio.run(generate_all_previews(dry_run=dry_run, voice_filter=voice))


if __name__ == "__main__":
    cyclopts.run(main)
