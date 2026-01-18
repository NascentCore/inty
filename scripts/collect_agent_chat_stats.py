#!/usr/bin/env python3
"""
CREATED_BY_AGENT

Collect agent chat statistics and upsert into agent_chat_stats.

Daily period uses UTC date boundaries. If the target date is Sunday (UTC),
weekly stats are also computed for Monday-Sunday and stored as:
YYYY-MM-DD-YYYY-MM-DD.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Dict, Iterable, Optional, Sequence, Tuple

import cyclopts
import sqlalchemy as sa
import yaml
from loguru import logger
from sqlalchemy import text
from sqlalchemy.engine import URL

DATE_FORMAT = "%Y-%m-%d"
DEFAULT_CONFIG_PATH = Path("config.yaml")
WEEKDAY_SUNDAY = 6


@dataclass
class AgentStatBucket:
    messages_count: int = 0
    users: set[str] = field(default_factory=set)


@dataclass
class PeriodSummary:
    period: str
    agent_rows: int
    session_rows: int
    unmatched_sessions: int
    total_messages: int
    total_users: int


def generate_session_id(chat_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chat_id))


def parse_target_date(target_date: Optional[str]) -> date:
    if target_date is None:
        return (datetime.now(timezone.utc) - timedelta(days=1)).date()
    return datetime.strptime(target_date, DATE_FORMAT).date()


def build_period_label(start_date: date, end_date: Optional[date] = None) -> str:
    if end_date is None:
        return start_date.strftime(DATE_FORMAT)
    return f"{start_date.strftime(DATE_FORMAT)}-{end_date.strftime(DATE_FORMAT)}"


def get_day_bounds(target_date: date) -> Tuple[datetime, datetime]:
    start = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def get_week_bounds(target_date: date) -> Tuple[date, date, datetime, datetime]:
    week_start = target_date - timedelta(days=target_date.weekday())
    week_end = week_start + timedelta(days=6)
    start, end = get_day_bounds(week_start)
    end = start + timedelta(days=7)
    return week_start, week_end, start, end


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    return config or {}


def build_database_url(config: dict) -> str:
    database = config.get("database") or {}
    url = database.get("url")
    if url:
        return url
    required = ["host", "port", "user", "password", "db"]
    missing = [key for key in required if database.get(key) in (None, "")]
    if missing:
        raise ValueError(f"Missing database config keys: {', '.join(missing)}")
    return str(
        URL.create(
            drivername="postgresql+psycopg",
            username=database["user"],
            password=database["password"],
            host=database["host"],
            port=int(database["port"]),
            database=database["db"],
        )
    )


def resolve_database_url(config_path: Path, db_url: Optional[str]) -> str:
    if db_url:
        return db_url
    config = load_config(config_path)
    return build_database_url(config)


def fetch_session_message_counts(
    conn: sa.Connection, start: datetime, end: datetime
) -> Dict[str, int]:
    query = text(
        """
        SELECT session_id::text AS session_id, COUNT(*) AS message_count
        FROM chat_history
        WHERE created_at >= :start
          AND created_at < :end
          AND deleted_at IS NULL
        GROUP BY session_id
        """
    )
    rows = conn.execute(query, {"start": start, "end": end}).fetchall()
    return {row[0]: row[1] for row in rows}


def fetch_chats(conn: sa.Connection) -> Sequence[Tuple[str, str, str]]:
    query = text("SELECT id, agent_id, user_id FROM chats")
    return conn.execute(query).fetchall()


def map_sessions_to_chats(
    chats: Iterable[Tuple[str, str, str]], session_ids: set[str]
) -> Tuple[Dict[str, Tuple[str, str]], int]:
    mapping: Dict[str, Tuple[str, str]] = {}
    duplicates = 0
    for chat_id, agent_id, user_id in chats:
        session_id = generate_session_id(chat_id)
        if session_id not in session_ids:
            continue
        if session_id in mapping:
            duplicates += 1
        mapping[session_id] = (agent_id, user_id)
    return mapping, duplicates


def aggregate_agent_stats(
    message_counts: Dict[str, int],
    session_to_chat: Dict[str, Tuple[str, str]],
) -> Tuple[Dict[str, AgentStatBucket], int]:
    stats: Dict[str, AgentStatBucket] = {}
    unmatched = 0
    for session_id, message_count in message_counts.items():
        mapping = session_to_chat.get(session_id)
        if mapping is None:
            unmatched += 1
            continue
        agent_id, user_id = mapping
        bucket = stats.setdefault(agent_id, AgentStatBucket())
        bucket.messages_count += message_count
        bucket.users.add(user_id)
    return stats, unmatched


def build_summary(
    period: str,
    agent_stats: Dict[str, AgentStatBucket],
    session_rows: int,
    unmatched_sessions: int,
) -> PeriodSummary:
    total_messages = sum(bucket.messages_count for bucket in agent_stats.values())
    total_users = sum(len(bucket.users) for bucket in agent_stats.values())
    return PeriodSummary(
        period=period,
        agent_rows=len(agent_stats),
        session_rows=session_rows,
        unmatched_sessions=unmatched_sessions,
        total_messages=total_messages,
        total_users=total_users,
    )


def build_rows(
    agent_stats: Dict[str, AgentStatBucket], period: str
) -> list[dict]:
    rows = []
    for agent_id, bucket in sorted(agent_stats.items(), key=lambda item: item[0]):
        rows.append(
            {
                "id": agent_id,
                "period": period,
                "messages_count": bucket.messages_count,
                "users_count": len(bucket.users),
            }
        )
    return rows


def upsert_agent_stats(conn: sa.Connection, rows: list[dict]) -> int:
    if not rows:
        return 0
    query = text(
        """
        INSERT INTO agent_chat_stats (id, period, messages_count, users_count)
        VALUES (:id, :period, :messages_count, :users_count)
        ON CONFLICT (id, period)
        DO UPDATE SET
            messages_count = EXCLUDED.messages_count,
            users_count = EXCLUDED.users_count
        """
    )
    conn.execute(query, rows)
    return len(rows)


def process_period(
    conn: sa.Connection,
    period_label: str,
    start: datetime,
    end: datetime,
    dry_run: bool,
) -> PeriodSummary:
    message_counts = fetch_session_message_counts(conn, start, end)
    if not message_counts:
        summary = build_summary(period_label, {}, 0, 0)
        logger.debug(f"[{period_label}] No messages found.")
        return summary

    session_ids = set(message_counts.keys())
    chats = fetch_chats(conn)
    session_to_chat, duplicates = map_sessions_to_chats(chats, session_ids)
    if duplicates:
        logger.debug(f"[{period_label}] Duplicate session mappings: {duplicates}")

    agent_stats, unmatched_sessions = aggregate_agent_stats(
        message_counts, session_to_chat
    )
    summary = build_summary(
        period_label, agent_stats, len(message_counts), unmatched_sessions
    )
    logger.debug(
        f"[{period_label}] agents={summary.agent_rows} "
        f"sessions={summary.session_rows} "
        f"unmatched_sessions={summary.unmatched_sessions} "
        f"messages={summary.total_messages} users={summary.total_users}"
    )

    rows = build_rows(agent_stats, period_label)
    if dry_run:
        logger.debug(f"[{period_label}] Dry run: {len(rows)} rows ready.")
        return summary

    upserted = upsert_agent_stats(conn, rows)
    logger.debug(f"[{period_label}] Upserted rows: {upserted}")
    return summary


def should_collect_weekly(target_date: date) -> bool:
    return target_date.weekday() == WEEKDAY_SUNDAY


def main(
    target_date: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--date",
            help="UTC date in YYYY-MM-DD (default: yesterday in UTC)",
        ),
    ] = None,
    config: Annotated[
        Path,
        cyclopts.Parameter(
            name="--config", help="Config YAML path (default: config.yaml)"
        ),
    ] = DEFAULT_CONFIG_PATH,
    db_url: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--db-url",
            help="Database URL override (sync driver only)",
        ),
    ] = None,
    apply: Annotated[
        bool,
        cyclopts.Parameter(
            name="--apply", help="Write results to database (default: dry-run)"
        ),
    ] = False,
    confirm: Annotated[
        bool,
        cyclopts.Parameter(
            name="--confirm", help="Confirm database writes when --apply is set"
        ),
    ] = False,
):
    if apply and not confirm:
        raise SystemExit("Refusing to write without --confirm.")

    resolved_date = parse_target_date(target_date)
    day_start, day_end = get_day_bounds(resolved_date)
    daily_period = build_period_label(resolved_date)
    dry_run = not apply

    db_url_resolved = resolve_database_url(config, db_url)
    engine = sa.create_engine(db_url_resolved)
    logger.debug(
        f"Collecting stats for {daily_period} (dry_run={dry_run})."
    )

    connection_ctx = engine.begin() if apply else engine.connect()
    with connection_ctx as conn:
        process_period(conn, daily_period, day_start, day_end, dry_run)
        if should_collect_weekly(resolved_date):
            week_start, week_end, week_start_dt, week_end_dt = get_week_bounds(
                resolved_date
            )
            weekly_period = build_period_label(week_start, week_end)
            logger.debug(f"Weekly boundary hit, collecting {weekly_period}.")
            process_period(conn, weekly_period, week_start_dt, week_end_dt, dry_run)


if __name__ == "__main__":
    cyclopts.run(main)
