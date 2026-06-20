#!/usr/bin/env python3
"""
从导出的对话记录中按当前代码逻辑抽取用户记忆（Part1）。

读取 dump_user_messages_for_memory.py 生成的 prompt 文件或 JSON，调用与 memory_extraction_service
相同的 LLM 与 _extract_part1_summary 逻辑，输出 Part1 摘要，用于复现和验证抽取结果。

用法（仓库根目录）:
  export PYTHONPATH=.
  python tools/scripts/run_extract_memory_from_dump.py --prompt-file output/user_messages_W8BD8PX00QCX_prompt.txt
  python tools/scripts/run_extract_memory_from_dump.py --json-file output/user_messages_W8BD8PX00QCX.json --output output/part1.txt
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import cyclopts
from loguru import logger

from app.api.types.llm_config import LLMConfig
from app.core.config import global_config_loaded_from_config_yaml
from app.services.memory_extraction_service import (
    MEMORY_EXTRACTION_RESPONSE_FORMAT,
    _load_prompt,
    _part1_from_content,
)
from app.core.llms.openai_client import chat_completion_for_extraction
from app.utils.openrouter_memory import DEFAULT_MEMORY_EXTRACTION_MODEL


def _full_prompt_from_json(json_path: Path) -> str:
    """从 dump 输出的 JSON 中取出 formatted_chat_text，拼接成与 extract_and_save 一致的 full_prompt。"""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    formatted = data.get("formatted_chat_text") or ""
    prompt = _load_prompt()
    return f"{prompt}\n\n---\n\n# User chat history\n\n{formatted}"


def _llm_config_from_app() -> LLMConfig:
    """与 extract_and_save 一致：优先使用 memory_extraction 配置。"""
    cfg = getattr(
        global_config_loaded_from_config_yaml,
        "memory_extraction",
        None,
    )
    if cfg and getattr(cfg, "model", None) and str(cfg.model).strip():
        model_name = str(cfg.model).strip()
        return LLMConfig(model=model_name, max_tokens=4000, temperature=0.3)
    return LLMConfig(
        model=DEFAULT_MEMORY_EXTRACTION_MODEL,
        max_tokens=4000,
        temperature=0.3,
    )


async def run(
    prompt_file: Optional[Path],
    json_path: Optional[Path],
    output_path: Optional[Path],
) -> int:
    if prompt_file is None and json_path is None:
        logger.error("必须指定 --prompt-file 或 --json 之一")
        return 1
    if prompt_file is not None and json_path is not None:
        logger.error("只能指定 --prompt-file 或 --json 之一")
        return 1

    if prompt_file is not None:
        if not prompt_file.exists():
            logger.error(f"文件不存在: {prompt_file}")
            return 1
        full_prompt = prompt_file.read_text(encoding="utf-8")
    else:
        if not json_path.exists():
            logger.error(f"文件不存在: {json_path}")
            return 1
        full_prompt = _full_prompt_from_json(json_path)

    llm_config = _llm_config_from_app()
    logger.debug(f"使用模型: {llm_config.model}")

    try:
        try:
            full_analysis, prompt_tokens, completion_tokens = (
                await chat_completion_for_extraction(
                    full_prompt,
                    llm_config=llm_config,
                    response_format=MEMORY_EXTRACTION_RESPONSE_FORMAT,
                )
            )
        except Exception as format_err:
            logger.debug(f"structured output 失败，回退自由文本: {format_err}")
            full_analysis, prompt_tokens, completion_tokens = (
                await chat_completion_for_extraction(
                    full_prompt, llm_config=llm_config
                )
            )
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        return 1

    if not full_analysis or len(full_analysis.strip()) < 10:
        logger.error("LLM 返回内容过短或为空")
        return 1

    part1 = _part1_from_content(full_analysis)
    logger.info(
        f"Part1 长度={len(part1)}，prompt_tokens={prompt_tokens}，completion_tokens={completion_tokens}"
    )

    print("## full_analysis (模型完整返回)")
    print("---")
    print(full_analysis)
    print()
    print("## Part1 (解析出的用户画像摘要)")
    print("---")
    print(part1)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(part1, encoding="utf-8")
        logger.info(f"已写入: {output_path}")
    return 0


def main(
    prompt_file: Annotated[
        Optional[Path],
        cyclopts.Parameter(
            help="dump 脚本生成的完整 prompt 文件路径（如 output/user_messages_xxx_prompt.txt）"
        ),
    ] = None,
    json_file: Annotated[
        Optional[Path],
        cyclopts.Parameter(
            help="dump 脚本生成的 JSON 路径；将用其中 formatted_chat_text 拼接 full_prompt"
        ),
    ] = None,
    output: Annotated[
        Optional[Path],
        cyclopts.Parameter(help="将 Part1 摘要写入该文件"),
    ] = None,
) -> None:
    sys.exit(asyncio.run(run(prompt_file, json_file, output)))


if __name__ == "__main__":
    app = cyclopts.App()
    app.default(main)
    app()
