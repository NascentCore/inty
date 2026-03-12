#!/usr/bin/env python3
"""
导出指定用户在指定时间点之前的全部对话消息及记忆抽取使用的完整 prompt，
便于复现和验证记忆抽取结果。不依赖 app.core.config 模块级加载，仅用配置文件中的 database.url 直连。
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

import cyclopts
import psycopg
from loguru import logger

# 仅加载配置工具，不触发 app.core.config
from app.utils.config import load_config

# 记忆抽取 prompt 模板路径（与 memory_extraction_service 一致）
_PROMPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "core"
    / "prompting"
    / "memory_extraction_prompt.txt"
)


def _load_prompt() -> str:
    if not _PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"Memory extraction prompt file not found: {_PROMPT_PATH}"
        )
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _session_id_from_chat_id(chat_id: str) -> str:
    """与 chat_service.generate_session_id 一致。"""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(chat_id)))


def _parse_message_row(raw) -> Optional[tuple[str, str]]:
    """从 chat_history.message 解析 (role, content)。与 memory_extraction_service 逻辑一致。"""
    try:
        if isinstance(raw, str):
            data = json.loads(raw)
        elif isinstance(raw, dict):
            data = raw
        else:
            data = json.loads(str(raw))
    except Exception:
        return None
    msg_type = data.get("type", "human")
    content = ""
    if "data" in data and isinstance(data["data"], dict) and "content" in data["data"]:
        content = data["data"]["content"] or ""
    elif "content" in data:
        content = data["content"] or ""
    role = "user" if msg_type in ("human", "HumanMessage") else "assistant"
    return (role, str(content))


def _format_chat_for_prompt(messages: list[tuple[str, str]]) -> str:
    """与 memory_extraction_service._format_chat_for_prompt 一致。"""
    lines = []
    for role, content in messages:
        label = "用户" if role == "user" else "AI"
        lines.append(f"**{label}**: {content}")
    return "\n".join(lines)


def _parse_before(value: Optional[str]) -> Optional[datetime]:
    """解析 ISO 格式时间戳，支持带或不带时区。"""
    if not value or not value.strip():
        return None
    value = value.strip()
    try:
        # fromisoformat 支持 2026-03-02T03:05:35 和 2026-03-02T03:05:35+00:00
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError as e:
        logger.error(f"无效的 --before 格式，应为 ISO 时间戳: {value} ({e})")
        sys.exit(1)


def run(
    config_path: str,
    user_id: str,
    before: Optional[str],
    output_dir: str,
) -> int:
    config = load_config(config_path)
    db_url = config.database.url
    before_dt = _parse_before(before)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    user_id_short = user_id.replace("-", "")[-12:] if len(user_id) > 12 else user_id

    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, agent_id FROM chats WHERE user_id = %s AND is_active = true",
                (user_id,),
            )
            rows = cur.fetchall()
    if not rows:
        logger.warning(f"未找到该用户的活跃会话: user_id={user_id}")
        result = {
            "user_id": user_id,
            "before": before_dt.isoformat() if before_dt else None,
            "total_messages": 0,
            "user_messages_count": 0,
            "ai_messages_count": 0,
            "chats": [],
            "messages": [],
            "formatted_chat_text": "",
            "full_prompt_length": 0,
        }
        json_path = out_dir / f"user_messages_{user_id_short}.json"
        json_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (out_dir / f"user_messages_{user_id_short}_prompt.txt").write_text(
            _load_prompt() + "\n\n---\n\n# User chat history\n\n(no messages)",
            encoding="utf-8",
        )
        logger.info(f"已写入 {json_path} 与 prompt txt（无消息）")
        return 0

    chat_infos = [(str(r[0]), str(r[1]) if r[1] else None) for r in rows]
    session_to_chat = {
        _session_id_from_chat_id(cid): (cid, aid) for cid, aid in chat_infos
    }
    session_ids = list(session_to_chat.keys())
    placeholders = ",".join("%s" for _ in session_ids)

    sql = f"""
        SELECT session_id::text, message, created_at
        FROM chat_history
        WHERE session_id::text IN ({placeholders}) AND deleted_at IS NULL
    """
    params: list = list(session_ids)
    if before_dt is not None:
        sql += " AND created_at < %s"
        params.append(before_dt)

    sql += " ORDER BY created_at ASC"

    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            raw_rows = cur.fetchall()

    # 按 session 统计条数
    session_counts: dict[str, int] = {sid: 0 for sid in session_ids}
    messages: list[dict[str, str]] = []
    for session_id, message_raw, _ in raw_rows:
        parsed = _parse_message_row(message_raw)
        if parsed is None:
            continue
        role, content = parsed
        session_counts[session_id] = session_counts.get(session_id, 0) + 1
        messages.append({"role": role, "content": content})

    chats_out = []
    for sid in session_ids:
        cid, aid = session_to_chat[sid]
        chats_out.append(
            {
                "chat_id": cid,
                "agent_id": aid,
                "message_count": session_counts.get(sid, 0),
            }
        )

    user_count = sum(1 for m in messages if m["role"] == "user")
    ai_count = len(messages) - user_count
    formatted_chat = _format_chat_for_prompt(
        [(m["role"], m["content"]) for m in messages]
    )
    prompt_template = _load_prompt()
    full_prompt = f"{prompt_template}\n\n---\n\n# User chat history\n\n{formatted_chat}"

    result = {
        "user_id": user_id,
        "before": before_dt.isoformat() if before_dt else None,
        "total_messages": len(messages),
        "user_messages_count": user_count,
        "ai_messages_count": ai_count,
        "chats": chats_out,
        "messages": messages,
        "formatted_chat_text": formatted_chat,
        "full_prompt_length": len(full_prompt),
    }

    json_path = out_dir / f"user_messages_{user_id_short}.json"
    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    prompt_path = out_dir / f"user_messages_{user_id_short}_prompt.txt"
    prompt_path.write_text(full_prompt, encoding="utf-8")

    logger.info(
        f"已写入 {json_path} 与 {prompt_path}，消息数={len(messages)}，full_prompt 长度={len(full_prompt)}"
    )
    return 0


def main(
    user_id: Annotated[
        str,
        cyclopts.Parameter(help="目标用户 ID（必填）"),
    ],
    config: Annotated[
        str,
        cyclopts.Parameter(help="配置文件路径"),
    ] = "config.yaml",
    before: Annotated[
        Optional[str],
        cyclopts.Parameter(
            help="只拉取该时间点之前的消息（ISO 格式，如 2026-03-02T03:05:35），用于复现某次提取；不指定则拉全量"
        ),
    ] = None,
    output_dir: Annotated[
        str,
        cyclopts.Parameter(help="输出目录"),
    ] = "output",
) -> None:
    sys.exit(run(config, user_id, before, output_dir))


if __name__ == "__main__":
    app = cyclopts.App()
    app.default(main)
    app()
