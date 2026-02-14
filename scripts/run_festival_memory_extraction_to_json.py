#!/usr/bin/env python3
"""
节日记忆抽取：接受与 evaluation 表单相同输入，执行与 POST /evaluation/admin/festival-memory-extraction/run 相同流程，
结果写入 JSON 文件而非 memory 表。

用法: export PYTHONPATH=.
  python scripts/run_festival_memory_extraction_to_json.py --festival-name 春节 --festival-date 2025-01-29 --prompt "..." --output out.json
  python scripts/run_festival_memory_extraction_to_json.py --festival-name 春节 --festival-date 2025-01-29 --prompt-file prompt.txt --output out.json --timezone Asia/Shanghai --min-rounds 10
  python scripts/run_festival_memory_extraction_to_json.py --festival-name 春节 --festival-date 2025-01-29 --prompt-file prompt.txt --output out.json --limit 1
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Annotated, Optional

import cyclopts

from app.core.logging import init_logger
from loguru import logger
init_logger()

CONFIG_YAML = "config.yaml"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _ensure_config(config_path: Optional[str]) -> None:
    cwd = Path.cwd()
    target = cwd / CONFIG_YAML
    if config_path:
        src = Path(config_path)
        if not src.is_absolute():
            src = _repo_root() / config_path
        shutil.copy2(src, target)
    else:
        if not target.exists():
            print(f"错误: 未指定 --config 且当前目录下不存在 {CONFIG_YAML}", file=sys.stderr)
            sys.exit(1)


async def _run(
    festival_name: str,
    festival_date: date,
    prompt: str,
    timezone: str,
    min_rounds: int,
    output_path: Path,
    config: Optional[str],
    limit: Optional[int] = None,
) -> None:
    _ensure_config(config)
    from app.core.config import global_config_loaded_from_config_yaml
    from app.db.session import AsyncSessionLocal
    from app.services.festival_memory_service import (
        get_pairs_with_min_rounds_in_window_sync,
        extract_festival_to_dict,
    )

    db_url = global_config_loaded_from_config_yaml.database.url
    pairs = get_pairs_with_min_rounds_in_window_sync(
        festival_date, db_url, min_rounds=min_rounds, timezone_str=timezone
    )
    if limit is not None:
        pairs = pairs[:limit]
    memories: list[dict] = []
    success = 0
    async with AsyncSessionLocal() as db:
        for user_id, agent_id in pairs:
            logger.debug(f"extracting festival memory for user_id={user_id} agent_id={agent_id}")
            d = await extract_festival_to_dict(
                user_id, agent_id, festival_name, festival_date, prompt, db=db
            )
            if d is not None:
                memories.append(d)
                success += 1
    query: dict = {
        "festival_name": festival_name,
        "festival_date": festival_date.isoformat(),
        "timezone": timezone,
        "min_rounds_in_window": min_rounds,
    }
    if limit is not None:
        query["limit"] = limit
    payload = {
        "query": query,
        "summary": {
            "total_pairs": len(pairs),
            "success_count": success,
            "failed_count": len(pairs) - success,
        },
        "memories": memories,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    n = len(pairs)
    print(f"Done: {n} pair(s) in window, {success} memory(ies) written to {output_path}")


def main(
    festival_name: Annotated[str, cyclopts.Parameter(name="--festival-name", help="节日名称")],
    festival_date: Annotated[str, cyclopts.Parameter(name="--festival-date", help="节日日期 YYYY-MM-DD")],
    output: Annotated[str, cyclopts.Parameter(name="--output", help="输出 JSON 文件路径")],
    prompt: Annotated[Optional[str], cyclopts.Parameter(name="--prompt", help="抽取提示词")] = None,
    prompt_file: Annotated[Optional[str], cyclopts.Parameter(name="--prompt-file", help="从文件读取提示词")] = None,
    timezone: Annotated[str, cyclopts.Parameter(name="--timezone")] = "UTC",
    min_rounds: Annotated[int, cyclopts.Parameter(name="--min-rounds")] = 50,
    limit: Annotated[
        Optional[int],
        cyclopts.Parameter(name="--limit", help="仅处理前 count 个 (user, agent) 对，不传则处理全部；便于测试"),
    ] = None,
    config: Annotated[Optional[str], cyclopts.Parameter(name="--config")] = None,
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if prompt_file is not None:
        prompt = Path(prompt_file).read_text(encoding="utf-8").strip()
    if prompt is None or not prompt:
        print("错误: 请提供 --prompt 或 --prompt-file", file=sys.stderr)
        sys.exit(1)
    parsed_date = date.fromisoformat(festival_date)
    logger.debug(f"All arguments: {locals()}")
    asyncio.run(
        _run(
            festival_name=festival_name,
            festival_date=parsed_date,
            prompt=prompt,
            timezone=timezone,
            min_rounds=min_rounds,
            output_path=Path(output),
            config=config,
            limit=limit,
        )
    )


if __name__ == "__main__":
    app = cyclopts.App(help="节日记忆抽取，结果写 JSON 不写库。")
    app.default(main)
    app()
