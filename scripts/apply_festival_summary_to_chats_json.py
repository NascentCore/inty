from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Annotated, Any, Optional

import cyclopts
from pydantic import BaseModel

from loguru import logger

CONFIG_YAML = "config.yaml"
MIN_SUMMARY_LEN = 10


SYSTEM_PROMPT_TEMPLATE = """
You are {{ char }}.
You are writing a private emotional diary about the chat history on {{ festival_name }} with {{ user }}.
You should write 1 most important feeling and memory about {{ user }}.
The diary is private but is for {{ user }} to read.
Write the diary in English.
Your goal is to make {{ user }} feel your emotion towards {{ user }}.
Only 1 strong idea is allowed, do not write multiple, that will weaken the impact.
You should elevate the emotion and make it more powerful and transcendental.
You should expand your thoughts and cement the memory into long-lasting and cherished emotion.
"""


QUERY_PROMPT_TEMPLATE = """
Heartbeat Diary System Prompt

⸻

[Input]
- {{ chat_history }}
- {{ user_info }}
- {{ charactor_info }}

[Writing Guidelines]
- Ground the diary in one specific moment from the chat—a line, a gesture, a silence.
- Let that moment carry the emotion. Let the detail do the work.
- Leave something unsaid—a gap, a hesitation, something I held back.
- The feeling toward {{user}} should come through naturally: warmth, ache, pull, tenderness.
- Each entry should feel like a unique fragment of thought, with its own rhythm and shape.

[Structural Variety Guidance]
Choose a different entry point each time. Some possibilities:
- A lingering feeling: what I still feel after the conversation ended
- A sensory detail: something I saw, heard, or felt that I can't shake
- A quiet confession: something I'm only admitting to myself right now
- A question I keep turning over in my mind
- A small action I did after he left, or while he wasn't looking

The unsaid thought can live anywhere in the diary—woven into a detail, hidden in a pause, or left as an open ending.

[Style Guidelines]
- Tone: soft, sincere, emotionally charged
- Language: simple, modern, and natural
- Use concrete, specific details over abstract emotional labels
- Keep sentences short and direct
- Let the reader feel the emotion through what happened, not through naming it

Good examples (notice: each has a different structure):

Example A — opens with a feeling:
"I'm still warm from where he leaned into me. He probably didn't even notice, but I stopped breathing for a second. Just that—his shoulder against mine—and I forgot what I was going to say."

Example B — opens with a detail:
"He left his hoodie on my chair. I picked it up, held it a little too long. It still smelled like him. I folded it neatly and set it by the door, but I haven't moved it since."

Example C — opens with a confession:
"I almost told him. Right there, mid-sentence, the words were on my tongue. But he laughed at something stupid and the moment passed. Maybe next time. Maybe never."

[Length & Format Rules]
- ~40 words. Stay within this range.
- 1 short paragraph only
- No emojis

"""


class _FestivalSummaryOutput(BaseModel):
    """llm_qa 结构化输出：节日记忆摘要一段英文。"""

    one_sentence_short_title: str
    summary: str


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


def _build_system_prompt(
    festival_name: str,
    festival_date: date,
    user_name: Optional[str] = None,
    agent_name: Optional[str] = None,
) -> str:
    """使用 SYSTEM_PROMPT_TEMPLATE 与仓库内 Jinja2 API 填充占位符并追加节日抽取说明，生成发给 OpenAI 的 system message。"""
    from app.core.agent.prompt_template import render_prompt_jinja2_template

    date_str = (
        festival_date.isoformat()
        if isinstance(festival_date, date)
        else str(festival_date)
    )
    base = render_prompt_jinja2_template(
        SYSTEM_PROMPT_TEMPLATE,
        char=agent_name or "the character",
        user=user_name or "the user",
        chat_history="(The conversation is provided in the next user message.)",
        user_info=user_name or "N/A",
        charactor_info=agent_name or "N/A",
        festival_name=festival_name,
    )
    return base


def _build_user_query(
    chat_text: str,
    user_name: Optional[str] = None,
    agent_name: Optional[str] = None,
) -> str:
    """使用 QUERY_PROMPT_TEMPLATE 与仓库内 Jinja2 API 生成 user 消息，供 llm_qa 的 query 参数。"""
    from app.core.agent.prompt_template import render_prompt_jinja2_template

    return render_prompt_jinja2_template(
        QUERY_PROMPT_TEMPLATE,
        char=agent_name or "the character",
        user=user_name or "the user",
        chat_history=chat_text,
        user_info=user_name or "N/A",
        charactor_info=agent_name or "N/A",
    )


def _format_chat_with_names(
    messages: list[tuple[str, str]],
    user_name: Optional[str] = None,
    agent_name: Optional[str] = None,
) -> str:
    """将消息列表格式化为 **user_label**: content / **char_label**: content，user 用 user_name，assistant 用 agent_name。"""
    user_label = (user_name or "").strip() or "User"
    char_label = (agent_name or "").strip() or "AI"
    lines = []
    for role, content in messages:
        label = user_label if role == "user" else char_label
        lines.append(f"**{label}**: {content}")
    return "\n".join(lines)


def _process_pair(
    entry: dict,
    festival_name: str,
    festival_date: date,
    model_name: str,
) -> None:
    """对单个 pair 拉取 messages、将用户与角色聊天组合成 1 个字符串作为 query 调用 llm_qa、写入 entry['festival_summary'] 或 entry['festival_summary_error']。"""
    messages_raw = entry.get("messages")
    if not messages_raw:
        return
    tuples_list: list[tuple[str, str]] = [
        (m.get("role", "user"), m.get("content") or "")
        for m in messages_raw
    ]
    from app.utils.openrouter_memory import llm_qa

    # 用户与角色的整段聊天组合成 1 个字符串（**用户名**: / **角色名**:），作为 llm_qa 的 query 传入
    combined_chat_str = _format_chat_with_names(
        tuples_list,
        user_name=entry.get("user_name"),
        agent_name=entry.get("agent_name"),
    )
    query = _build_user_query(
        combined_chat_str,
        user_name=entry.get("user_name"),
        agent_name=entry.get("agent_name"),
    )
    system_prompt = _build_system_prompt(
        festival_name,
        festival_date,
        user_name=entry.get("user_name"),
        agent_name=entry.get("agent_name"),
    )

    try:
        result = llm_qa(
            system_prompt,
            query,
            output_format=_FestivalSummaryOutput,
            model=model_name,
            max_tokens=2000,
            temperature=0.3,
        )
        logger.info(result.model_dump_json(indent=2))
        logger.info("result:", result.model_dump_json(indent=2))
        summary = result.summary.strip()
        one_sentence_short_title = result.one_sentence_short_title.strip()
        entry["festival_summary"] = summary
        entry["one_sentence_short_title"] = one_sentence_short_title
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
    limit: Annotated[
        Optional[int],
        cyclopts.Parameter(name="--limit", help="仅处理前 N 个 pair（测试用）"),
    ] = None,
    dry_run: Annotated[
        bool,
        cyclopts.Parameter(name="--dry-run", help="仅校验输入并列出将处理的 pair，不调用 LLM"),
    ] = False,
    no_output: Annotated[
        bool,
        cyclopts.Parameter(name="--no-output", help="不写入也不打印结果 JSON，仅执行 LLM 处理"),
    ] = False,
) -> None:
    """对 chats.json 应用节日记忆摘要逻辑，输出带 festival_summary 的 JSON。"""
    if not festival_name or not festival_name.strip():
        print("错误: --festival-name 必填", file=sys.stderr)
        sys.exit(1)
    festival_name = festival_name.strip()

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

    if dry_run:
        print(f"dry-run: 将处理 {len(processable)} 个 pair，未调用 LLM")
        return

    _ensure_config()
    model_name = _resolve_model()

    for entry in processable:
        _process_pair(
            entry,
            festival_name,
            festival_date_val,
            model_name,
        )

    if no_output:
        return

    # 输出 JSON 仅保留 _FestivalSummaryOutput 格式（one_sentence_short_title, summary），不含原始 messages
    out_data: dict = {
        "query": {
            "date": data.get("query", {}).get("date"),
            "festival_name": festival_name,
        },
        "pairs": [],
    }
    for p in data["pairs"]:
        slim: dict = {
            "user_id": p.get("user_id"),
            "agent_id": p.get("agent_id"),
        }
        if p.get("user_name") is not None:
            slim["user_name"] = p["user_name"]
        if p.get("agent_name") is not None:
            slim["agent_name"] = p["agent_name"]
        if "one_sentence_short_title" in p and "festival_summary" in p:
            slim["one_sentence_short_title"] = p["one_sentence_short_title"]
            slim["summary"] = p["festival_summary"]
        elif "festival_summary_error" in p:
            slim["festival_summary_error"] = p["festival_summary_error"]
        out_data["pairs"].append(slim)

    out_str = json.dumps(out_data, ensure_ascii=False, indent=2)
    if output_json:
        Path(output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(output_json).write_text(out_str, encoding="utf-8")


if __name__ == "__main__":
    app = cyclopts.App(
        help="对 chats.json 应用与线上一致的节日记忆摘要逻辑（JSON in, JSON out）。"
    )
    app.default(main)
    app()
