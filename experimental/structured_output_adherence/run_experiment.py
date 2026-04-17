#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

_PKG = Path(__file__).resolve().parent
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from db_util import (  # noqa: E402
    connect_db,
    count_history_rows,
    fetch_random_active_chat_ids,
    load_chat_history,
    session_id_for_chat,
)
from messages import parse_lc_message_row, transcript_upto  # noqa: E402
from schema import ConversationScenario, response_format_json_schema_strict  # noqa: E402


SYSTEM_PROMPT = """You label a private chat transcript for internal research.
Return ONLY one JSON object. No markdown fences. No outer wrapper key.
The top-level keys must be exactly: title, one_line_summary, inferred_topics, emotional_tone, contains_sensitive_content, confidence_0_1.
emotional_tone must be exactly one of these strings: warm, tense, playful, supportive, conflicted, neutral, other.
If the transcript is empty, still return valid JSON with neutral fields."""


USER_TEMPLATE = """Transcript (oldest to newest, same language as users wrote):

---
{transcript}
---

Infer labels for the situation so far (not the next reply).

Example shape (values are illustrative only):
{{"title":"...","one_line_summary":"...","inferred_topics":["..."],"emotional_tone":"neutral","contains_sensitive_content":false,"confidence_0_1":0.7}}"""


@dataclass
class TurnResult:
    chat_id: str
    session_id: str
    turn_index: int
    ok: bool
    error: Optional[str]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    latency_ms: float
    raw_head: str


def _parse_iso_utc(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _load_fixture(path: Path) -> List[Tuple[str, List[Dict[str, str]]]]:
    """
    Each JSONL line: {"chat_id": "...", "messages": [{"role":"user|assistant|system","content":"..."}]}
    Legacy: {"chat_id": "...", "turns": ["..."]} (treated as user-only lines).
    """
    out: List[Tuple[str, List[Dict[str, str]]]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            cid = str(obj["chat_id"])
            if "messages" in obj:
                msgs = []
                for m in obj["messages"]:
                    role = str(m.get("role", "user")).lower()
                    if role not in ("user", "assistant", "system"):
                        role = "user"
                    msgs.append({"role": role, "content": str(m.get("content", ""))})
                out.append((cid, msgs))
            else:
                turns = obj.get("turns") or []
                msgs = [{"role": "user", "content": str(t)} for t in turns]
                out.append((cid, msgs))
    return out


def _ensure_out_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _call_model(
    client: OpenAI,
    model: str,
    transcript: str,
    temperature: float,
    max_tokens: int,
    use_strict_schema: bool,
) -> tuple[str, Optional[int], Optional[int], float, Optional[str]]:
    user_content = USER_TEMPLATE.format(transcript=transcript or "(empty)")
    formats: List[Optional[dict]] = []
    if use_strict_schema:
        formats.append(response_format_json_schema_strict())
    formats.append({"type": "json_object"})

    last_err: Optional[str] = None
    t0 = time.perf_counter()
    for fmt in formats:
        try:
            resp = client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                response_format=fmt,
            )
            elapsed = (time.perf_counter() - t0) * 1000.0
            content = (resp.choices[0].message.content or "").strip()
            usage = resp.usage
            pt = usage.prompt_tokens if usage else None
            ct = usage.completion_tokens if usage else None
            return content, pt, ct, elapsed, None
        except Exception as e:
            last_err = str(e)
            t0 = time.perf_counter()
            continue
    elapsed = (time.perf_counter() - t0) * 1000.0
    return "", None, None, elapsed, last_err


def _normalize_scenario_json_text(content: str) -> str:
    """
    If the model wraps the payload as {"ConversationScenario": {...}}, unwrap once.
    Root must still be the scenario object for Pydantic.
    """
    raw = content.strip()
    if not raw:
        return raw
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if not isinstance(data, dict):
        return raw
    inner = data.get("ConversationScenario")
    if isinstance(inner, dict) and len(data) == 1:
        return json.dumps(inner, ensure_ascii=False)
    return raw


def _evaluate_content(content: str) -> tuple[bool, Optional[str]]:
    if not content.strip():
        return False, "empty_content"
    normalized = _normalize_scenario_json_text(content)
    try:
        ConversationScenario.model_validate_json(normalized)
        return True, None
    except Exception as e:
        return False, f"schema:{e.__class__.__name__}:{e}"


def run_on_transcripts(
    client: Optional[OpenAI],
    model: str,
    items: List[tuple[str, List[Dict[str, str]]]],
    max_steps: int,
    stride: int,
    temperature: float,
    max_tokens: int,
    use_strict_schema: bool,
    dry_run: bool,
    out_path: Path,
) -> Dict[str, Any]:
    results: List[TurnResult] = []
    for chat_id, parsed in items:
        sid = session_id_for_chat(chat_id)
        n = len(parsed)
        indices = list(range(0, n, max(1, stride)))
        if max_steps:
            indices = indices[:max_steps]
        for turn_index in indices:
            transcript = transcript_upto(parsed, turn_index)
            if dry_run:
                ok, err = True, None
                content = ConversationScenario(
                    title="dry",
                    one_line_summary="dry run",
                    inferred_topics=["fixture"],
                    emotional_tone="neutral",
                    contains_sensitive_content=False,
                    confidence_0_1=1.0,
                ).model_dump_json()
                pt, ct, ms = None, None, 0.0
            else:
                assert client is not None
                content, pt, ct, ms, api_err = _call_model(
                    client,
                    model,
                    transcript,
                    temperature,
                    max_tokens,
                    use_strict_schema,
                )
                if api_err:
                    ok, err = False, f"api:{api_err}"
                else:
                    ok, err = _evaluate_content(content)
            raw_head = (content or "")[:200].replace("\n", " ")
            results.append(
                TurnResult(
                    chat_id=chat_id,
                    session_id=sid,
                    turn_index=turn_index,
                    ok=ok,
                    error=err,
                    prompt_tokens=pt,
                    completion_tokens=ct,
                    latency_ms=ms,
                    raw_head=raw_head,
                )
            )

    _write_jsonl(out_path, results)
    return _summarize(results)


def _write_jsonl(path: Path, results: List[TurnResult]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")


def _summarize(results: List[TurnResult]) -> Dict[str, Any]:
    n = len(results)
    ok = sum(1 for r in results if r.ok)
    return {
        "n_calls": n,
        "adherence_rate": ok / n if n else 0.0,
        "failure_count": n - ok,
        "failures_by_error": _bucket_errors(results),
    }


def _bucket_errors(results: List[TurnResult]) -> Dict[str, int]:
    buckets: Dict[str, int] = {}
    for r in results:
        if r.ok:
            continue
        key = (r.error or "unknown").split(":", 2)[0]
        buckets[key] = buckets.get(key, 0) + 1
    return buckets


def _pick_chats(
    conn: Any,
    sample_chats: int,
    min_rows: int,
    since: Optional[datetime],
    until: Optional[datetime],
    pool_factor: int,
) -> List[str]:
    pool = max(sample_chats * pool_factor, sample_chats * 5)
    candidates = fetch_random_active_chat_ids(conn, pool)
    picked: List[str] = []
    for cid in candidates:
        sid = session_id_for_chat(cid)
        if count_history_rows(conn, sid, since, until) >= min_rows:
            picked.append(cid)
        if len(picked) >= sample_chats:
            break
    return picked


def main() -> int:
    load_dotenv(Path(__file__).resolve().parent / ".env")
    parser = argparse.ArgumentParser(
        description="Replay chat_history and measure structured JSON adherence."
    )
    parser.add_argument("--config", default=None, help="Path to config.yaml for DB.")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Overrides DATABASE_URL / config.yaml database.",
    )
    parser.add_argument("--sample-chats", type=int, default=0)
    parser.add_argument("--min-rows", type=int, default=10)
    parser.add_argument("--max-turns-per-chat", type=int, default=20)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--since", default=None, help="ISO date/datetime UTC lower bound.")
    parser.add_argument("--until", default=None, help="ISO date/datetime UTC upper bound (exclusive).")
    parser.add_argument("--fixture", default=None, help="JSONL fixture: {chat_id, turns: [text...]}")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default="openai/gpt-4o-mini")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--no-strict-schema", action="store_true")
    parser.add_argument("--out-dir", default="experimental/structured_output_adherence/out")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    database_url = args.database_url or os.getenv("DATABASE_URL")
    since = _parse_iso_utc(args.since)
    until = _parse_iso_utc(args.until)

    out_dir = Path(args.out_dir)
    _ensure_out_dir(out_dir)
    jsonl_path = out_dir / "turns.jsonl"
    summary_path = out_dir / "summary.json"

    use_strict = not args.no_strict_schema

    client: Optional[OpenAI] = None
    if not args.dry_run:
        base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENROUTER_BASE_URL")
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Missing OPENROUTER_API_KEY or OPENAI_API_KEY", file=sys.stderr)
            return 2
        kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        elif os.getenv("OPENROUTER_API_KEY"):
            kwargs["base_url"] = "https://openrouter.ai/api/v1"
        client = OpenAI(**kwargs)

    items: List[tuple[str, List[Dict[str, str]]]] = []

    if args.fixture:
        fix_path = Path(args.fixture)
        items.extend(_load_fixture(fix_path))
    elif args.sample_chats > 0:
        conn = connect_db(args.config, database_url)
        try:
            chat_ids = _pick_chats(
                conn,
                args.sample_chats,
                args.min_rows,
                since,
                until,
                pool_factor=30,
            )
            if len(chat_ids) < args.sample_chats:
                print(
                    f"Only found {len(chat_ids)} chats with >= {args.min_rows} rows.",
                    file=sys.stderr,
                )
            for cid in chat_ids:
                sid = session_id_for_chat(cid)
                hist = load_chat_history(conn, sid, since, until)
                msgs: List[Dict[str, str]] = []
                for row in hist[: args.max_turns_per_chat]:
                    p = parse_lc_message_row(row.message)
                    msgs.append({"role": p["role"], "content": p["content"]})
                items.append((cid, msgs))
        finally:
            conn.close()
    else:
        print("Provide --fixture ... or --sample-chats N", file=sys.stderr)
        return 2

    summary = run_on_transcripts(
        client,
        args.model,
        items,
        max_steps=args.max_turns_per_chat,
        stride=args.stride,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        use_strict_schema=use_strict,
        dry_run=args.dry_run,
        out_path=jsonl_path,
    )
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
