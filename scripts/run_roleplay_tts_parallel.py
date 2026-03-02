#!/usr/bin/env python3
"""
使用助理内容字符串调用 synthesize_with_roleplay_prompt()，并行跑多段文本并写出 WAV 以验证结果。

用法:
    # 使用内置示例（一段带括号的对话）并行跑 2 次
    PYTHONPATH=. python scripts/run_roleplay_tts_parallel.py --text "..." --text "..."

    # 从 JSON 读入所有 role=assistant 的 content，并行合成并写出到 out/
    PYTHONPATH=. python scripts/run_roleplay_tts_parallel.py --file-json tests/files/erotic_messages_sample.json --output-dir out

    # 限制并发数
    PYTHONPATH=. python scripts/run_roleplay_tts_parallel.py --file-json tests/files/erotic_messages_sample.json --concurrency 2
"""

import asyncio
import json
from pathlib import Path
from typing import Annotated, List, Optional

import cyclopts
from loguru import logger

# 内置示例：与 tts_api.santize_text_for_gemini_tts 文档中的格式一致
DEFAULT_SAMPLE = '''(After your successful presentation, your secretary entered your room to congratulate you.)
"So, you're tired aren't you?"
(She closes the door behind her and locks it)
"sir, what can I do for you..?"
'''


async def _synthesize_one(
    api: "GeminiTTSAPI",
    index: int,
    text: str,
    voice_id: str,
    model_id: str,
    output_dir: Path,
    semaphore: Optional[asyncio.Semaphore],
    total: int,
) -> tuple[int, bool, Optional[Path]]:
    """对一段助理内容调用 synthesize_with_roleplay_prompt，写出 WAV；返回 (index, ok, path)."""
    async def _run() -> tuple[bool, Optional[Path]]:
        from app.core.voice.tts_api import TTSRequest

        req = TTSRequest(
            text=text.strip(),
            voice_id=voice_id,
            model_id=model_id,
            output_format="mp3_44100_128",
        )
        result = await api.synthesize_with_roleplay_prompt(req)
        if not result:
            return False, None
        out_path = output_dir / f"{index}.wav"
        out_path.write_bytes(result.audio_bytes)
        return True, out_path

    if semaphore:
        async with semaphore:
            ok, path = await _run()
    else:
        ok, path = await _run()
    status = f"OK {path}" if ok else "FAIL"
    logger.info(f"Segment [{index}] done: {status} ({index + 1}/{total})")
    return index, ok, path


async def run_parallel(
    texts: List[str],
    output_dir: Path,
    voice_id: str = "Zephyr",
    concurrency: Optional[int] = None,
) -> dict[int, tuple[bool, Optional[Path]]]:
    """
    并行对多段助理内容调用 synthesize_with_roleplay_prompt，结果写入 output_dir/{0,1,...}.wav。
    """
    from app.core.voice.tts_api import (
        DEFAULT_GEMINI_TTS_MODEL,
        GeminiTTSAPI,
    )

    api = GeminiTTSAPI()
    sem = asyncio.Semaphore(concurrency) if concurrency else None
    total = len(texts)
    logger.info(f"Synthesizing {total} segments to {output_dir}")

    tasks = [
        _synthesize_one(
            api,
            i,
            t,
            voice_id=voice_id,
            model_id=DEFAULT_GEMINI_TTS_MODEL,
            output_dir=output_dir,
            semaphore=sem,
            total=total,
        )
        for i, t in enumerate(texts)
    ]
    results_list = await asyncio.gather(*tasks)
    return {idx: (ok, path) for idx, ok, path in results_list}


def main(
    text: Annotated[
        Optional[List[str]],
        cyclopts.Parameter(
            name="--text",
            help="助理内容字符串，可多次传入以跑多段",
        ),
    ] = None,
    file: Annotated[
        Optional[Path],
        cyclopts.Parameter(
            name="--file-json",
            help="从 JSON 文件读入多段助理内容",
        ),
    ] = None,
    output_dir: Annotated[
        Path,
        cyclopts.Parameter(
            name="--output-dir",
            help="WAV 输出目录",
        ),
    ] = Path("scripts/out_roleplay_tts"),
    voice: Annotated[
        str,
        cyclopts.Parameter(
            name="--voice",
            help="Gemini 音色名",
        ),
    ] = "Zephyr",
    concurrency: Annotated[
        Optional[int],
        cyclopts.Parameter(
            name="--concurrency",
            help="最大并发请求数，不传则全部并行",
        ),
    ] = None,
):
    """使用助理内容调用 roleplay TTS，并行执行并写出 WAV 验证。"""
    if file is not None:
        data = json.loads(file.read_text())
        messages = data.get("messages") or []
        texts = [m["content"].strip() for m in messages if m.get("role") == "assistant" and (m.get("content") or "").strip()]
    elif text and len(text) > 0:
        texts = [t.strip() for t in text if t.strip()]
    else:
        texts = [DEFAULT_SAMPLE.strip()]

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    results = asyncio.run(
        run_parallel(
            texts=texts,
            output_dir=output_dir,
            voice_id=voice,
            concurrency=concurrency,
        )
    )
    ok_count = sum(1 for ok, _ in results.values() if ok)
    fail_count = len(results) - ok_count
    logger.info(f"Done. {ok_count} OK, {fail_count} FAIL")


if __name__ == "__main__":
    cyclopts.run(main)
