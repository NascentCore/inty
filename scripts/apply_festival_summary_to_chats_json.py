#!/usr/bin/env python3
"""
对 query_chat_history_by_date.py 导出的 chats.json 应用与线上一致的节日记忆摘要逻辑：
格式化会话、构建 prompt、调用 OpenRouter 抽取摘要，为每个 (user_id, agent_id) 写入 festival_summary。

输入 JSON 须由 query_chat_history_by_date.py --include-messages 生成（含 pairs[].messages）。
运行前需保证当前目录下存在 config.yaml（用于 OpenRouter 等配置）。

用法:
    export PYTHONPATH=.
    python scripts/apply_festival_summary_to_chats_json.py --input-json chats.json --festival-name "Christmas" --prompt-file prompt.txt --output-json out.json
    python scripts/apply_festival_summary_to_chats_json.py -i chats.json --festival-name "Valentine's Day" --prompt "..." --limit 2 --dry-run

选项: --input-json/-i, --output-json/-o, --festival-name, --festival-date（可选，默认用 JSON 内 query.date）,
      --prompt/--prompt-file, --limit, --dry-run
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Annotated, Any, Optional

import cyclopts

logger = logging.getLogger(__name__)

CONFIG_YAML = "config.yaml"
MIN_SUMMARY_LEN = 10


def _ensure_config() -> None:
    """要求当前目录下存在 config.yaml，否则退出。"""
    cwd = Path.cwd()
    target = cwd / CONFIG_YAML
    if not target.exists():
        print(
            f"错误: 当前目录下不存在 {CONFIG_YAML}，请在仓库根目录运行或先创建 config.yaml",
            file=sys.stderr,
        )
        sys.exit(1)


def _build_full_prompt(
    prompt_template: str,
    festival_name: str,
    festival_date: date,
    chat_text: str,
) -> str:
    """与 festival_memory_service.extract_festival_and_save 中 prompt 构建一致。"""
    date_str = (
        festival_date.isoformat()
        if isinstance(festival_date, date)
        else str(festival_date)
    )
    return f"""{prompt_template}

---
Festival name: {festival_name}
Festival date: {date_str}

---
# Conversation between the user and the character

{chat_text}

---
Based on the conversation above, extract memories or preferences related to "{festival_name}" for this user and character. Output a concise summary in one short paragraph. Output the summary in English only. Do not include any other format or text."""


async def _process_pair(
    entry: dict,
    festival_name: str,
    festival_date: date,
    prompt_template: str,
    model_name: str,
) -> None:
    """对单个 pair 拉取 messages、调用 LLM、写入 entry['festival_summary'] 或 entry['festival_summary_error']。"""
    messages_raw = entry.get("messages")
    if not messages_raw:
        logger.debug("跳过无 messages 的 pair: user_id=%s agent_id=%s", entry.get("user_id"), entry.get("agent_id"))
        return
    tuples_list: list[tuple[str, str]] = [
        (m.get("role", "user"), m.get("content") or "")
        for m in messages_raw
    ]
    from app.services.festival_memory_service import _format_chat_for_prompt
    from app.utils.openrouter_memory import call_openrouter_for_extraction

    chat_text = _format_chat_for_prompt(tuples_list)
    full_prompt = _build_full_prompt(
        prompt_template, festival_name, festival_date, chat_text
    )
    try:
        summary, _, _ = await call_openrouter_for_extraction(
            full_prompt,
            model=model_name,
            max_tokens=2000,
            temperature=0.3,
        )
        if not summary or len(summary.strip()) < MIN_SUMMARY_LEN:
            raise ValueError("Extraction result is too short or empty")
        entry["festival_summary"] = summary.strip()
        if "festival_summary_error" in entry:
            del entry["festival_summary_error"]
    except Exception as e:
        logger.warning(
            "节日记忆抽取失败 user_id=%s agent_id=%s: %s",
            entry.get("user_id"),
            entry.get("agent_id"),
            e,
        )
        entry["festival_summary_error"] = str(e)
        if "festival_summary" in entry:
            del entry["festival_summary"]


def _resolve_model() -> str:
    """与 extract_festival_and_save 一致：memory_extraction.model 或默认。"""
    from app.core.config import global_config_loaded_from_config_yaml
    from app.utils.openrouter_memory import (
        DEFAULT_MEMORY_EXTRACTION_MODEL as DEFAULT_FESTIVAL_EXTRACTION_MODEL,
    )

    cfg = getattr(global_config_loaded_from_config_yaml, "memory_extraction", None)
    model_name = (
        cfg.model.strip() if cfg and cfg.model else None
    ) or DEFAULT_FESTIVAL_EXTRACTION_MODEL
    return model_name


def main(
    input_json: Annotated[
        str,
        cyclopts.Parameter(name=["--input-json", "-i"], help="chats.json 路径"),
    ] = "chats.json",
    output_json: Annotated[
        Optional[str],
        cyclopts.Parameter(name=["--output-json", "-o"], help="结果 JSON 路径，不指定则输出到 stdout"),
    ] = None,
    festival_name: Annotated[
        str,
        cyclopts.Parameter(name="--festival-name", help="节日名称，用于 prompt 中的抽取目标"),
    ] = "",
    festival_date: Annotated[
        Optional[str],
        cyclopts.Parameter(name="--festival-date", help="节日日期 YYYY-MM-DD，不指定则使用输入 JSON 的 query.date"),
    ] = None,
    prompt: Annotated[
        Optional[str],
        cyclopts.Parameter(name="--prompt", help="节日记忆 prompt 模板正文"),
    ] = None,
    prompt_file: Annotated[
        Optional[str],
        cyclopts.Parameter(name="--prompt-file", help="从文件读取 prompt 模板"),
    ] = None,
    limit: Annotated[
        Optional[int],
        cyclopts.Parameter(name="--limit", help="仅处理前 N 个 pair（测试用）"),
    ] = None,
    dry_run: Annotated[
        bool,
        cyclopts.Parameter(name="--dry-run", help="仅校验输入并列出将处理的 pair，不调用 LLM"),
    ] = False,
) -> None:
    """对 chats.json 应用节日记忆摘要逻辑，输出带 festival_summary 的 JSON。"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not festival_name or not festival_name.strip():
        print("错误: --festival-name 必填", file=sys.stderr)
        sys.exit(1)
    festival_name = festival_name.strip()

    if (prompt is not None) == (prompt_file is not None):
        print("错误: 必须且仅能指定 --prompt 或 --prompt-file 其一", file=sys.stderr)
        sys.exit(1)
    if prompt_file is not None:
        path = Path(prompt_file)
        if not path.exists():
            print(f"错误: prompt 文件不存在: {path}", file=sys.stderr)
            sys.exit(1)
        prompt = path.read_text(encoding="utf-8")
    assert prompt is not None

    input_path = Path(input_json)
    if not input_path.exists():
        print(f"错误: 输入文件不存在: {input_path}", file=sys.stderr)
        sys.exit(1)
    with open(input_path, encoding="utf-8") as f:
        data: dict = json.load(f)
    if "pairs" not in data:
        print("错误: 输入 JSON 缺少 'pairs'", file=sys.stderr)
        sys.exit(1)
    pairs: list[dict] = data["pairs"]

    # 解析 festival_date：优先 CLI，否则 query.date
    if festival_date is not None:
        try:
            parsed_date = date.fromisoformat(festival_date)
        except ValueError:
            print(f"错误: 无效日期 {festival_date!r}，应为 YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)
    else:
        query = data.get("query") or {}
        qdate = query.get("date")
        if not qdate:
            print("错误: 未指定 --festival-date 且输入 JSON 无 query.date", file=sys.stderr)
            sys.exit(1)
        try:
            parsed_date = date.fromisoformat(qdate)
        except ValueError:
            print(f"错误: 输入 JSON query.date 无效: {qdate!r}", file=sys.stderr)
            sys.exit(1)
    festival_date_val = parsed_date

    processable = [p for p in pairs if p.get("messages")]
    if limit is not None:
        processable = processable[: limit]
    logger.info(
        "将处理 %s 个 pair（共 %s 个含 messages）",
        len(processable),
        len([p for p in pairs if p.get("messages")]),
    )
    for p in pairs:
        if "messages" not in p:
            logger.debug("跳过无 messages: user_id=%s agent_id=%s", p.get("user_id"), p.get("agent_id"))

    if dry_run:
        for i, p in enumerate(processable):
            logger.info(
                "[dry-run] %s: user_id=%s agent_id=%s messages=%s",
                i + 1,
                p.get("user_id"),
                p.get("agent_id"),
                len(p.get("messages", [])),
            )
        print(f"dry-run: 将处理 {len(processable)} 个 pair，未调用 LLM")
        return

    _ensure_config()
    model_name = _resolve_model()
    logger.debug("使用模型: %s", model_name)

    async def run_all() -> None:
        for idx, entry in enumerate(processable):
            await _process_pair(
                entry,
                festival_name,
                festival_date_val,
                prompt,
                model_name,
            )
            if (idx + 1) % 10 == 0 or idx + 1 == len(processable):
                logger.info("已处理 %s/%s pair", idx + 1, len(processable))

    asyncio.run(run_all())

    out_str = json.dumps(data, ensure_ascii=False, indent=2)
    if output_json:
        Path(output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(output_json).write_text(out_str, encoding="utf-8")
        logger.info("已写入 %s", output_json)
    else:
        print(out_str)


if __name__ == "__main__":
    app = cyclopts.App(
        help="对 chats.json 应用与线上一致的节日记忆摘要逻辑（JSON in, JSON out）。"
    )
    app.default(main)
    app()
