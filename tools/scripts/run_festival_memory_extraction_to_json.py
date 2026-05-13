"""
节日记忆抽取：接受与 evaluation 表单相同输入，执行与 POST /evaluation/admin/festival-memory-extraction/run 相同流程，
结果写入 JSON 文件而非 memory 表。

注意⚠️：由于时间有限，本脚本只是使用了与 POST /evaluation/admin/festival-memory-extraction/run 完全一样的代码，
实际上生成的结果要与其完全一致，需要更多的修改来确定输入完全一致，目前还做不到。

--output 不传时，根据节日名、日期、prompt 来源、模式及可选参数自动生成可识别的输出路径，便于从文件名看出所用参数。

输出格式（breaking change）：每条记忆为 { user_id, agent_id, memory_type, content, metadata, user_name?, agent_name? }。
metadata 为 FestivalMemoryMetadata（festival_name, festival_date, llm_config）；不再包含顶级的 festival_name、festival_date、llm_config。

--messages-output：仅抽取模式下生效，将每对 (user, agent) 的会话消息写入指定 JSON。
--messages-input：从上述 JSON 读入消息并做抽取，与直接抽取结果一致；与 --query 互斥。
--parallel-workers N：运行最多 N 个并发抽取（OpenAI 调用）；不传或 1 为顺序执行。
--llm <openrouter-model-id>：覆盖用于摘要的模型（如 openrouter/...）；不传则用配置/默认模型。

用法: export PYTHONPATH=.
  python tools/scripts/run_festival_memory_extraction_to_json.py --festival-name 春节 --festival-date 2025-01-29 --prompt "..." --output out.json
  python tools/scripts/run_festival_memory_extraction_to_json.py --festival-name 春节 --festival-date 2025-01-29 --prompt-file prompt.txt --output out.json --timezone Asia/Shanghai --min-rounds 10
  python tools/scripts/run_festival_memory_extraction_to_json.py --festival-name "2026 Valentine's Day" --festival-date 2026-02-14 --prompt-file festival_memory_prompt_1.txt
  # 上例不传 --output 时写入当前目录，如 2026_valentines_day_2026-02-14_festival_memory_prompt_1.json
  python tools/scripts/run_festival_memory_extraction_to_json.py --festival-name 春节 --festival-date 2025-01-29 --prompt-file prompt.txt --output out.json --limit 1
  python tools/scripts/run_festival_memory_extraction_to_json.py --festival-name 春节 --festival-date 2025-01-29 --prompt-file prompt.txt --output out.json --messages-output msgs.json
  python tools/scripts/run_festival_memory_extraction_to_json.py --festival-name 春节 --festival-date 2025-01-29 --prompt-file prompt.txt --output out2.json --messages-input msgs.json
  python tools/scripts/run_festival_memory_extraction_to_json.py --festival-name "测试节日20260201" --festival-date 2026-02-01 --prompt-file festival_memory_prompt.txt --output tmp/backend_out.json --timezone America/Los_Angeles --min-rounds 50 --query
  python tools/scripts/run_festival_memory_extraction_to_json.py ... --parallel-workers 4
  python tools/scripts/run_festival_memory_extraction_to_json.py ... --llm openrouter/anthropic/claude-3.5-sonnet
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Annotated, Optional, Tuple

import cyclopts

from app.api.types.llm_config import LLMConfig
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
            print(
                f"错误: 未指定 --config 且当前目录下不存在 {CONFIG_YAML}",
                file=sys.stderr,
            )
            sys.exit(1)


def _memory_sort_key(item: dict) -> tuple[str, str]:
    """与 sort_festival_memory_json 一致的 (user_name, agent_name) 排序键。"""
    return (
        item.get("user_name") or item.get("user_id") or "",
        item.get("agent_name") or item.get("agent_id") or "",
    )


def _sanitize_slug(s: str, max_len: int = 60) -> str:
    """Replace path-unsafe or awkward chars with underscore, collapse/strip, cap length."""
    if not s or not isinstance(s, str):
        return ""
    # Replace space, apostrophe, path separators and common unsafe chars with underscore
    out = re.sub(r"[\s'\/\\:*?\"<>|]+", "_", s)
    out = re.sub(r"_+", "_", out).strip("_")
    if len(out) > max_len:
        out = out[:max_len].rstrip("_")
    return out


def _derive_output_path(
    festival_name: str,
    festival_date: date,
    *,
    query: bool = False,
    messages_input: Optional[str] = None,
    prompt_file: Optional[str] = None,
    llm: Optional[str] = None,
    parallel_workers: Optional[int] = None,
    limit: Optional[int] = None,
) -> Path:
    """
    根据 main 参数拼出可识别的输出文件名，放在当前工作目录。
    格式: {festival_slug}_{date}[_mode_or_prompt][_llm_...][_wN][_limitN].json
    """
    slug = _sanitize_slug(festival_name)
    date_str = (
        festival_date.isoformat()
        if isinstance(festival_date, date)
        else str(festival_date)
    )
    parts = [slug, date_str]
    if query:
        parts.append("query")
    elif messages_input:
        stem = Path(messages_input).stem
        if stem:
            parts.append(_sanitize_slug(stem, max_len=40))
        else:
            parts.append("messages")
    else:
        if prompt_file:
            stem = Path(prompt_file).stem
            parts.append(_sanitize_slug(stem, max_len=40) if stem else "inline")
        else:
            parts.append("inline")
    if llm and llm.strip():
        # Short model id: last segment after /, then sanitize
        raw = llm.strip().split("/")[-1] if "/" in llm else llm.strip()
        parts.append("llm_" + _sanitize_slug(raw, max_len=40))
    if parallel_workers is not None and parallel_workers >= 2:
        parts.append(f"w{parallel_workers}")
    if limit is not None:
        parts.append(f"limit{limit}")
    basename = "_".join(parts) + ".json"
    return Path.cwd() / "tmp" / basename


async def _run(
    festival_name: str,
    festival_date: date,
    prompt: str,
    timezone: str,
    min_rounds: int,
    output_path: Path,
    config: Optional[str],
    limit: Optional[int] = None,
    messages_output_path: Optional[Path] = None,
    parallel_workers: Optional[int] = None,
    llm_model_id: Optional[str] = None,
) -> None:
    _ensure_config(config)
    from app.core.config import global_config_loaded_from_config_yaml
    from app.db.session import AsyncSessionLocal
    from app.services.festival_memory_service import (
        get_messages_for_user_agent_sync,
        get_pairs_with_min_rounds_in_window_sync,
        extract_festival_to_dict,
    )

    llm_config = (
        LLMConfig(model=llm_model_id.strip())
        if (llm_model_id and llm_model_id.strip())
        else None
    )
    db_url = global_config_loaded_from_config_yaml.database.url
    pairs = get_pairs_with_min_rounds_in_window_sync(
        festival_date, db_url, min_rounds=min_rounds, timezone_str=timezone
    )
    if limit is not None:
        pairs = pairs[:limit]
    memories: list[dict] = []
    pairs_messages: list[dict] = []
    success = 0
    use_parallel = parallel_workers is not None and parallel_workers >= 2
    if use_parallel:
        sem = asyncio.Semaphore(parallel_workers)

        async def _extract_one(
            user_id: str, agent_id: str
        ) -> Tuple[Optional[dict], Optional[dict]]:
            async with sem:
                async with AsyncSessionLocal() as db:
                    logger.debug(
                        f"extracting festival memory for user_id={user_id} agent_id={agent_id}"
                    )
                    pair_message: Optional[dict] = None
                    if messages_output_path is not None:
                        messages = await asyncio.to_thread(
                            get_messages_for_user_agent_sync, user_id, agent_id
                        )
                        pair_message = {
                            "user_id": user_id,
                            "agent_id": agent_id,
                            "messages": [
                                {"role": r, "content": c} for r, c in messages
                            ],
                        }
                    d = await extract_festival_to_dict(
                        user_id,
                        agent_id,
                        festival_name,
                        festival_date,
                        prompt,
                        db=db,
                        llm_config=llm_config,
                    )
                    return (d, pair_message)

        results = await asyncio.gather(*[_extract_one(uid, aid) for uid, aid in pairs])
        for d, pair_message in results:
            if d is not None:
                memories.append(d)
                success += 1
            if pair_message is not None:
                pairs_messages.append(pair_message)
    else:
        async with AsyncSessionLocal() as db:
            for user_id, agent_id in pairs:
                logger.debug(
                    f"extracting festival memory for user_id={user_id} agent_id={agent_id}"
                )
                if messages_output_path is not None:
                    messages = await asyncio.to_thread(
                        get_messages_for_user_agent_sync, user_id, agent_id
                    )
                    pairs_messages.append(
                        {
                            "user_id": user_id,
                            "agent_id": agent_id,
                            "messages": [
                                {"role": r, "content": c} for r, c in messages
                            ],
                        }
                    )
                d = await extract_festival_to_dict(
                    user_id,
                    agent_id,
                    festival_name,
                    festival_date,
                    prompt,
                    db=db,
                    llm_config=llm_config,
                )
                if d is not None:
                    memories.append(d)
                    success += 1
    if messages_output_path is not None:
        messages_query: dict = {
            "festival_name": festival_name,
            "festival_date": festival_date.isoformat(),
            "timezone": timezone,
            "min_rounds_in_window": min_rounds,
        }
        if limit is not None:
            messages_query["limit"] = limit
        messages_payload = {
            "query": messages_query,
            "pairs_messages": pairs_messages,
        }
        messages_output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(messages_output_path, "w", encoding="utf-8") as f:
            json.dump(messages_payload, f, ensure_ascii=False, indent=2)
        print(f"Messages written to {messages_output_path}")
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
        "memories": sorted(memories, key=_memory_sort_key),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    n = len(pairs)
    print(
        f"Done: {n} pair(s) in window, {success} memory(ies) written to {output_path}"
    )


def _load_pairs_messages_from_file(
    path: Path,
) -> tuple[list[tuple[str, str]], dict[tuple[str, str], list[tuple[str, str]]], dict]:
    """读入 --messages-output 写出的 JSON，返回 (pairs 有序列表, (user_id, agent_id) -> messages, query 元数据)。"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "query" not in data or "pairs_messages" not in data:
        raise ValueError(f"JSON 缺少 query 或 pairs_messages: {path}")
    pairs: list[tuple[str, str]] = []
    messages_map: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for item in data["pairs_messages"]:
        user_id = item["user_id"]
        agent_id = item["agent_id"]
        messages = [(m["role"], m["content"]) for m in item["messages"]]
        pairs.append((user_id, agent_id))
        messages_map[(user_id, agent_id)] = messages
    return pairs, messages_map, data["query"]


async def _run_from_messages_file(
    festival_name: str,
    festival_date: date,
    prompt: str,
    output_path: Path,
    config: Optional[str],
    messages_input_path: Path,
    parallel_workers: Optional[int] = None,
    llm_model_id: Optional[str] = None,
) -> None:
    """从 --messages-output 写出的 JSON 读入 pairs 与消息，用 messages_override 做抽取，输出格式与 _run 一致。"""
    _ensure_config(config)
    pairs, messages_map, file_query = _load_pairs_messages_from_file(
        messages_input_path
    )
    from app.db.session import AsyncSessionLocal
    from app.services.festival_memory_service import extract_festival_to_dict

    llm_config = (
        LLMConfig(model=llm_model_id.strip())
        if (llm_model_id and llm_model_id.strip())
        else None
    )
    memories: list[dict] = []
    success = 0
    use_parallel = parallel_workers is not None and parallel_workers >= 2
    if use_parallel:
        sem = asyncio.Semaphore(parallel_workers)

        async def _extract_one_from_messages(
            user_id: str, agent_id: str
        ) -> Optional[dict]:
            async with sem:
                async with AsyncSessionLocal() as db:
                    messages = messages_map.get((user_id, agent_id), [])
                    logger.debug(
                        f"extracting from messages file for user_id={user_id} agent_id={agent_id}"
                    )
                    return await extract_festival_to_dict(
                        user_id,
                        agent_id,
                        festival_name,
                        festival_date,
                        prompt,
                        db=db,
                        messages_override=messages,
                        llm_config=llm_config,
                    )

        results = await asyncio.gather(
            *[_extract_one_from_messages(uid, aid) for uid, aid in pairs]
        )
        for d in results:
            if d is not None:
                memories.append(d)
                success += 1
    else:
        async with AsyncSessionLocal() as db:
            for user_id, agent_id in pairs:
                messages = messages_map.get((user_id, agent_id), [])
                logger.debug(
                    f"extracting from messages file for user_id={user_id} agent_id={agent_id}"
                )
                d = await extract_festival_to_dict(
                    user_id,
                    agent_id,
                    festival_name,
                    festival_date,
                    prompt,
                    db=db,
                    messages_override=messages,
                    llm_config=llm_config,
                )
                if d is not None:
                    memories.append(d)
                    success += 1
    query: dict = dict(file_query)
    query["festival_name"] = festival_name
    query["festival_date"] = festival_date.isoformat()
    payload = {
        "query": query,
        "summary": {
            "total_pairs": len(pairs),
            "success_count": success,
            "failed_count": len(pairs) - success,
        },
        "memories": sorted(memories, key=_memory_sort_key),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    n = len(pairs)
    print(
        f"Done: {n} pair(s) from messages file, {success} memory(ies) written to {output_path}"
    )


async def _run_query(
    festival_name: str,
    festival_date: date,
    timezone: str,
    output_path: Path,
    config: Optional[str],
) -> None:
    """仅从 memory 表查询已有节日记忆并写 JSON，不执行抽取。"""
    _ensure_config(config)
    from app.db.session import AsyncSessionLocal
    from app.services.festival_memory_service import query_festival_memories_from_db

    async with AsyncSessionLocal() as db:
        memories = await query_festival_memories_from_db(
            db, festival_name, festival_date
        )
    query_meta: dict = {
        "festival_name": festival_name,
        "festival_date": festival_date.isoformat(),
        "timezone": timezone,
    }
    payload = {
        "query": query_meta,
        "summary": {"total_count": len(memories)},
        "memories": sorted(memories, key=_memory_sort_key),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Query done: {len(memories)} memory(ies) written to {output_path}")


def main(
    festival_name: Annotated[
        str, cyclopts.Parameter(name="--festival-name", help="节日名称")
    ],
    festival_date: Annotated[
        str, cyclopts.Parameter(name="--festival-date", help="节日日期 YYYY-MM-DD")
    ],
    output: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--output",
            help="输出 JSON 文件路径；不传则根据节日名、日期、prompt 来源等参数自动生成可识别的文件名",
        ),
    ] = None,
    prompt: Annotated[
        Optional[str], cyclopts.Parameter(name="--prompt", help="抽取提示词")
    ] = None,
    prompt_file: Annotated[
        Optional[str], cyclopts.Parameter(name="--prompt-file", help="从文件读取提示词")
    ] = None,
    timezone: Annotated[str, cyclopts.Parameter(name="--timezone")] = "UTC",
    min_rounds: Annotated[int, cyclopts.Parameter(name="--min-rounds")] = 50,
    limit: Annotated[
        Optional[int],
        cyclopts.Parameter(
            name="--limit",
            help="仅处理前 count 个 (user, agent) 对，不传则处理全部；便于测试",
        ),
    ] = None,
    config: Annotated[Optional[str], cyclopts.Parameter(name="--config")] = None,
    query: Annotated[
        bool,
        cyclopts.Parameter(name="--query", help="仅查询 memory 表已有结果，不执行抽取"),
    ] = False,
    messages_output: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--messages-output",
            help="将每对 (user, agent) 的会话消息写入该 JSON 文件（仅抽取模式生效）",
        ),
    ] = None,
    messages_input: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--messages-input",
            help="从 --messages-output 写出的 JSON 读入消息并用于抽取，与直接抽取结果一致；与 --query 互斥",
        ),
    ] = None,
    parallel_workers: Annotated[
        Optional[int],
        cyclopts.Parameter(
            name="--parallel-workers",
            help="Run up to N concurrent extractions (OpenAI calls). Omit or 1 for sequential.",
        ),
    ] = None,
    llm: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--llm",
            help="OpenRouter model id for summarization (e.g. openrouter/anthropic/claude-3.5-sonnet). Omit to use config/default.",
        ),
    ] = None,
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parsed_date = date.fromisoformat(festival_date)
    logger.debug(f"All arguments: {locals()}")
    if query and messages_input:
        print("错误: --query 与 --messages-input 不能同时使用", file=sys.stderr)
        sys.exit(1)
    if parallel_workers is not None and parallel_workers < 1:
        print("错误: --parallel-workers 必须 >= 1", file=sys.stderr)
        sys.exit(1)
    output_path = (
        Path(output)
        if output is not None
        else _derive_output_path(
            festival_name=festival_name,
            festival_date=parsed_date,
            query=query,
            messages_input=messages_input,
            prompt_file=prompt_file,
            llm=llm,
            parallel_workers=parallel_workers,
            limit=limit,
        )
    )
    if query:
        asyncio.run(
            _run_query(
                festival_name=festival_name,
                festival_date=parsed_date,
                timezone=timezone,
                output_path=output_path,
                config=config,
            )
        )
        return
    if prompt_file is not None:
        prompt = Path(prompt_file).read_text(encoding="utf-8").strip()
    if prompt is None or not prompt:
        print("错误: 请提供 --prompt 或 --prompt-file", file=sys.stderr)
        sys.exit(1)
    if messages_input:
        asyncio.run(
            _run_from_messages_file(
                festival_name=festival_name,
                festival_date=parsed_date,
                prompt=prompt,
                output_path=output_path,
                config=config,
                messages_input_path=Path(messages_input),
                parallel_workers=parallel_workers,
                llm_model_id=llm,
            )
        )
        return
    asyncio.run(
        _run(
            festival_name=festival_name,
            festival_date=parsed_date,
            prompt=prompt,
            timezone=timezone,
            min_rounds=min_rounds,
            output_path=output_path,
            config=config,
            limit=limit,
            messages_output_path=Path(messages_output) if messages_output else None,
            parallel_workers=parallel_workers,
            llm_model_id=llm,
        )
    )


if __name__ == "__main__":
    app = cyclopts.App(help="节日记忆抽取，结果写 JSON 不写库。")
    app.default(main)
    app()
