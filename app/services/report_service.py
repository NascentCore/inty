import re
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, bindparam, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.uuid import get_new_report_id
from app.models.report import (
    FEEDBACK_REASON_ID_TO_CODE,
    REASON_ID_TO_CODE,
    Report,
    ReportType,
)
from app.models.user import User
from app.schemas.report import ReportCreate, ReportQuery, ReportReason

GITHUB_ISSUE_URL_PATTERN = re.compile(
    r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/\d+/?(?:[?#].*)?$"
)
MESSAGE_TYPE_FILTER_SQL = (
    "ch.meta_data->>'messageType' IS NULL OR "
    "(ch.meta_data->>'messageType' != 'festival_memory_prompt' "
    "AND ch.meta_data->>'messageType' != 'daily_memory_prompt')"
)
OPENING_FILTER_SQL = (
    "ch.meta_data IS NULL OR ch.meta_data->>'isOpening' IS NULL OR "
    "ch.meta_data->>'isOpening' != 'true'"
)


def list_report_reasons() -> List[ReportReason]:
    """返回硬编码的举报原因列表（不再从数据库查询）"""
    return [
        ReportReason(
            id=id,
            code=code,
            description=None,
            is_active=True,
        )
        for id, code in REASON_ID_TO_CODE.items()
    ]


async def _get_users_by_ids(
    db: AsyncSession, user_ids: List[str]
) -> dict[str, User]:
    unique_user_ids = list({user_id for user_id in user_ids if user_id})
    if not unique_user_ids:
        return {}

    result = await db.execute(select(User).where(User.id.in_(unique_user_ids)))
    users = result.scalars().all()
    return {user.id: user for user in users}


def _attach_reporter_user_info(
    reports: List[Report], users_by_id: dict[str, User]
) -> None:
    for report in reports:
        report.reporter_user_info = users_by_id.get(report.reporter_id)


def _generate_session_id(chat_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chat_id))


async def create_report(
    db: AsyncSession, report_in: ReportCreate, reporter_id: str
) -> Report:
    report_id = get_new_report_id()

    # 处理 reason_codes 和向后兼容的 reason_ids
    reason_codes = report_in.reason_codes
    reason_ids = []

    # 如果提供了 reason_ids（向后兼容），转换为 reason_codes
    if report_in.reason_ids:
        # 根据 report_type 选择使用哪个映射
        # 如果 report_type 为 None，默认为 REPORT
        is_feedback = report_in.report_type == ReportType.FEEDBACK
        id_to_code_map = (
            FEEDBACK_REASON_ID_TO_CODE if is_feedback else REASON_ID_TO_CODE
        )

        # 使用硬编码的映射关系转换
        if not reason_codes:
            # 验证所有 reason_ids 都存在，如果不存在则抛出错误
            missing_ids = [
                rid for rid in report_in.reason_ids if rid not in id_to_code_map
            ]
            if missing_ids:
                raise ValueError(
                    f"Invalid reason_ids: {missing_ids}. These reason IDs do not exist."
                )
            # id_to_code_map 返回的是字符串，需要转换为枚举
            from app.schemas.report import ReasonCode

            reason_codes = [
                ReasonCode(id_to_code_map[rid]) for rid in report_in.reason_ids
            ]
        # 为了向后兼容，仍然保存 reason_ids
        reason_ids = report_in.reason_ids

    # 验证至少提供了 reason_codes 或 reason_ids，且 reason_codes 包含至少一个非空值
    if not reason_codes or not any(reason_codes):
        raise ValueError(
            "Either reason_codes or reason_ids must be provided, and reason_codes must contain at least one non-empty value"
        )

    # 将枚举值转换为字符串（如果 reason_codes 是枚举列表）
    # 用于存储到数据库（数据库字段是 ARRAY(String)）
    if reason_codes:
        reason_codes_str = [
            code.value if hasattr(code, "value") else str(code)
            for code in reason_codes
        ]
    else:
        reason_codes_str = []

    # 如果 report_type 为 None，则存储为 None（数据库为 NULL），业务逻辑中视为 REPORT
    report = Report(
        id=report_id,
        target_id=report_in.target_id,
        target_type=report_in.target_type,
        reporter_id=reporter_id,
        reason_ids=reason_ids
        or [],  # 向后兼容，如果只有 reason_codes 则为空列表
        reason_codes=reason_codes_str,
        image_urls=report_in.image_urls or [],
        description=report_in.description,
        report_type=report_in.report_type,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def query_reports(db: AsyncSession, query: ReportQuery):
    filters = []
    # DEPRECATED: 支持通过 reason_ids 查询（向后兼容）
    if query.reason_ids:
        filters.append(Report.reason_ids.overlap(query.reason_ids))
    # 支持通过 reason_codes 查询
    if query.reason_codes:
        # 将枚举值转换为字符串（如果 reason_codes 是枚举列表）
        reason_codes_str = [
            code.value if hasattr(code, "value") else code
            for code in query.reason_codes
        ]
        filters.append(Report.reason_codes.overlap(reason_codes_str))
    if query.target_id:
        filters.append(Report.target_id == query.target_id)
    if query.target_type:
        filters.append(Report.target_type == query.target_type)
    if query.status:
        filters.append(Report.status == query.status)
    if query.reporter_id:
        filters.append(Report.reporter_id == query.reporter_id)
    if query.report_type:
        # 如果查询 REPORT，需要包含 report_type 为 NULL 的记录（NULL 视为 REPORT）
        if query.report_type == ReportType.REPORT:
            filters.append(
                (Report.report_type == ReportType.REPORT)
                | (Report.report_type.is_(None))
            )
        else:
            filters.append(Report.report_type == query.report_type)

    # 查询总数
    count_stmt = select(func.count()).select_from(Report).where(and_(*filters))
    total = (await db.execute(count_stmt)).scalar_one()

    # 构建排序
    order_clause = Report.created_at.desc()  # 默认按创建时间降序
    if query.order_by == "created_at_asc":
        order_clause = Report.created_at.asc()

    # 查询分页数据
    stmt = (
        select(Report)
        .where(and_(*filters))
        .order_by(order_clause)
        .offset(query.skip)
        .limit(query.limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    # 确保 reason_codes 存在（向后兼容：如果只有 reason_ids，转换为 reason_codes）
    for item in items:
        # 如果 reason_codes 为空但 reason_ids 存在，从 reason_ids 转换
        if not item.reason_codes and item.reason_ids:
            # 根据 report_type 选择使用哪个映射
            # 如果 report_type 为 None，默认为 REPORT
            is_feedback = item.report_type == ReportType.FEEDBACK
            id_to_code_map = (
                FEEDBACK_REASON_ID_TO_CODE if is_feedback else REASON_ID_TO_CODE
            )
            # 使用硬编码的映射关系转换，只转换存在的 ID
            converted_codes = [
                id_to_code_map[rid]
                for rid in item.reason_ids
                if rid in id_to_code_map
            ]
            item.reason_codes = converted_codes if converted_codes else []

    # 确保所有字段在序列化前都是正确的类型（处理 None 值）
    for item in items:
        # 确保 reason_ids 是列表（不能是 None）
        if item.reason_ids is None:
            item.reason_ids = []
        # 确保 reason_codes 是列表（不能是 None）
        if item.reason_codes is None:
            item.reason_codes = []
        # 如果 report_type 为 None，在序列化时视为 "REPORT"
        if item.report_type is None:
            item.report_type = ReportType.REPORT

    users_by_id = await _get_users_by_ids(
        db,
        [item.reporter_id for item in items],
    )
    _attach_reporter_user_info(items, users_by_id)

    return items, total


async def get_report(db: AsyncSession, report_id: str) -> Report:
    """按 id 获取单条举报，不存在时抛出 ValueError。"""
    report = (
        await db.execute(select(Report).where(Report.id == report_id))
    ).scalar_one_or_none()
    if not report:
        raise ValueError("Report not found")
    if report.reason_codes is None and report.reason_ids:
        is_feedback = report.report_type == ReportType.FEEDBACK
        id_to_code_map = (
            FEEDBACK_REASON_ID_TO_CODE if is_feedback else REASON_ID_TO_CODE
        )
        report.reason_codes = [
            id_to_code_map[rid]
            for rid in report.reason_ids
            if rid in id_to_code_map
        ] or []
    if report.reason_ids is None:
        report.reason_ids = []
    if report.reason_codes is None:
        report.reason_codes = []
    if report.report_type is None:
        report.report_type = ReportType.REPORT

    users_by_id = await _get_users_by_ids(db, [report.reporter_id])
    _attach_reporter_user_info([report], users_by_id)
    return report


def _normalize_github_issue_url(github_issue: Optional[str]) -> Optional[str]:
    if github_issue is None:
        return None

    normalized_url = github_issue.strip()
    if not normalized_url:
        return None

    if not GITHUB_ISSUE_URL_PATTERN.match(normalized_url):
        raise ValueError(
            "Invalid GitHub issue URL format. Expected: https://github.com/<owner>/<repo>/issues/<number>"
        )
    return normalized_url


async def update_report_github_issue(
    db: AsyncSession, report_id: str, github_issue: Optional[str]
) -> Report:
    report = (
        await db.execute(select(Report).where(Report.id == report_id))
    ).scalar_one_or_none()
    if not report:
        raise ValueError("Report not found")

    report.github_issue = _normalize_github_issue_url(github_issue)
    await db.commit()
    return await get_report(db, report_id)


async def get_report_conversation_groups(
    db: AsyncSession, user_id: str
) -> List[Dict[str, Any]]:
    chats_stmt = text("""
        SELECT
            c.id AS chat_id,
            c.user_id,
            c.agent_id,
            a.name AS agent_name,
            c.created_at
        FROM chats c
        LEFT JOIN agents a ON c.agent_id = a.id
        WHERE c.user_id = :user_id
        ORDER BY c.created_at DESC
    """)
    chats_result = await db.execute(chats_stmt, {"user_id": user_id})
    chat_rows = chats_result.fetchall()
    if not chat_rows:
        return []

    chat_ids = [row[0] for row in chat_rows]
    chat_to_session = {
        chat_id: _generate_session_id(chat_id) for chat_id in chat_ids
    }
    session_ids = list(chat_to_session.values())

    stats_stmt = text(f"""
        SELECT
            ch.session_id::text AS session_id,
            COUNT(*) FILTER (
                WHERE ch.message->>'type' = 'human' AND ({OPENING_FILTER_SQL})
            ) AS round_count,
            MAX(ch.created_at) AS latest_message_at
        FROM chat_history ch
        WHERE ch.deleted_at IS NULL
          AND ({MESSAGE_TYPE_FILTER_SQL})
          AND ch.session_id::text IN :session_ids
        GROUP BY ch.session_id
    """).bindparams(bindparam("session_ids", expanding=True))
    stats_result = await db.execute(stats_stmt, {"session_ids": session_ids})
    session_stats = {
        row[0]: {"round_count": row[1] or 0, "latest_message_at": row[2]}
        for row in stats_result.fetchall()
    }

    grouped: Dict[tuple[str, str], Dict[str, Any]] = {}
    for row in chat_rows:
        chat_id = row[0]
        current_user_id = row[1]
        agent_id = row[2]
        agent_name = row[3]
        chat_created_at = row[4]
        session_id = chat_to_session[chat_id]
        current_stats = session_stats.get(
            session_id, {"round_count": 0, "latest_message_at": None}
        )
        latest_message_at = (
            current_stats["latest_message_at"] or chat_created_at
        )
        group_key = (current_user_id, agent_id)

        if group_key not in grouped:
            grouped[group_key] = {
                "user_id": current_user_id,
                "agent_id": agent_id,
                "agent_name": agent_name,
                "chat_count": 0,
                "total_rounds": 0,
                "latest_message_at": latest_message_at,
            }

        grouped_item = grouped[group_key]
        grouped_item["chat_count"] += 1
        grouped_item["total_rounds"] += current_stats["round_count"]
        if latest_message_at and (
            grouped_item["latest_message_at"] is None
            or latest_message_at > grouped_item["latest_message_at"]
        ):
            grouped_item["latest_message_at"] = latest_message_at

    grouped_items = list(grouped.values())
    grouped_items.sort(
        key=lambda item: (
            item["latest_message_at"] is not None,
            item["latest_message_at"],
            item["agent_id"],
        ),
        reverse=True,
    )
    return grouped_items


async def get_report_conversation_messages(
    db: AsyncSession,
    *,
    user_id: str,
    agent_id: str,
    page: int = 1,
    size: int = 20,
) -> Dict[str, Any]:
    chats_stmt = text("""
        SELECT c.id
        FROM chats c
        WHERE c.user_id = :user_id
          AND c.agent_id = :agent_id
        ORDER BY c.created_at DESC
    """)
    chats_result = await db.execute(
        chats_stmt, {"user_id": user_id, "agent_id": agent_id}
    )
    chat_ids = [row[0] for row in chats_result.fetchall()]
    if not chat_ids:
        return {
            "user_id": user_id,
            "agent_id": agent_id,
            "page": page,
            "size": size,
            "total_rounds": 0,
            "has_more": False,
            "messages": [],
        }

    chat_to_session = {
        chat_id: _generate_session_id(chat_id) for chat_id in chat_ids
    }
    session_to_chat = {
        session_id: chat_id for chat_id, session_id in chat_to_session.items()
    }
    session_ids = list(chat_to_session.values())

    total_rounds_stmt = text(f"""
        SELECT COUNT(*)
        FROM chat_history ch
        WHERE ch.deleted_at IS NULL
          AND ({MESSAGE_TYPE_FILTER_SQL})
          AND ch.message->>'type' = 'human'
          AND ({OPENING_FILTER_SQL})
          AND ch.session_id::text IN :session_ids
    """).bindparams(bindparam("session_ids", expanding=True))
    total_rounds_result = await db.execute(
        total_rounds_stmt, {"session_ids": session_ids}
    )
    total_rounds = total_rounds_result.scalar() or 0
    if total_rounds == 0:
        return {
            "user_id": user_id,
            "agent_id": agent_id,
            "page": page,
            "size": size,
            "total_rounds": 0,
            "has_more": False,
            "messages": [],
        }

    offset_rounds = (page - 1) * size
    messages_stmt = text(f"""
        WITH filtered AS (
            SELECT
                ch.id,
                ch.session_id::text AS session_id,
                ch.message->>'type' AS message_type,
                COALESCE(
                    ch.message->'data'->>'content',
                    ch.message->>'content'
                ) AS content,
                ch.message->'data'->>'image_url' AS image_url_from_message,
                ch.created_at,
                ch.audio_url,
                ch.meta_data
            FROM chat_history ch
            WHERE ch.deleted_at IS NULL
              AND ({MESSAGE_TYPE_FILTER_SQL})
              AND ch.session_id::text IN :session_ids
        ),
        annotated AS (
            SELECT
                f.*,
                SUM(
                    CASE
                        WHEN f.message_type = 'human'
                         AND (
                            f.meta_data IS NULL
                            OR f.meta_data->>'isOpening' IS NULL
                            OR f.meta_data->>'isOpening' != 'true'
                         )
                        THEN 1
                        ELSE 0
                    END
                ) OVER (ORDER BY f.created_at ASC, f.id ASC) AS round_no
            FROM filtered f
        ),
        with_totals AS (
            SELECT
                a.*,
                MAX(a.round_no) OVER () AS total_rounds
            FROM annotated a
        ),
        windowed AS (
            SELECT
                wt.*,
                CASE
                    WHEN wt.round_no <= 0 THEN NULL
                    ELSE wt.total_rounds - wt.round_no + 1
                END AS reverse_round_no
            FROM with_totals wt
        )
        SELECT
            id,
            session_id,
            message_type,
            content,
            image_url_from_message,
            created_at,
            audio_url,
            meta_data
        FROM windowed
        WHERE reverse_round_no IS NOT NULL
          AND reverse_round_no > :offset_rounds
          AND reverse_round_no <= :offset_rounds_plus_size
        ORDER BY created_at DESC, id DESC
    """).bindparams(bindparam("session_ids", expanding=True))
    rows_result = await db.execute(
        messages_stmt,
        {
            "session_ids": session_ids,
            "offset_rounds": offset_rounds,
            "offset_rounds_plus_size": offset_rounds + size,
        },
    )
    rows = rows_result.fetchall()

    from app.services.image_transform_service import image_transform_service

    messages: List[Dict[str, Any]] = []
    for row in rows:
        message_type = row[2] or "human"
        image_url = row[4]
        if message_type == "image" and image_url:
            image_url = image_transform_service.transform_desktop(image_url)

        meta_data = row[7]
        if (
            isinstance(meta_data, dict)
            and isinstance(meta_data.get("generated_image"), dict)
            and meta_data["generated_image"].get("image_url")
        ):
            generated_image = dict(meta_data["generated_image"])
            generated_image["image_url"] = (
                image_transform_service.transform_desktop(
                    generated_image["image_url"]
                )
            )
            meta_data = dict(meta_data)
            meta_data["generated_image"] = generated_image

        session_id = row[1]
        messages.append(
            {
                "id": row[0],
                "chat_id": session_to_chat.get(session_id, ""),
                "message_type": message_type,
                "content": row[3],
                "image_url": image_url,
                "created_at": row[5],
                "audio_url": row[6],
                "meta_data": meta_data,
            }
        )

    return {
        "user_id": user_id,
        "agent_id": agent_id,
        "page": page,
        "size": size,
        "total_rounds": total_rounds,
        "has_more": offset_rounds + size < total_rounds,
        "messages": messages,
    }


async def delete_report(
    db: AsyncSession,
    report_id: str,
    *,
    current_user_id: str,
    is_superuser: bool,
) -> None:
    report = (
        await db.execute(select(Report).where(Report.id == report_id))
    ).scalar_one_or_none()
    if not report:
        raise ValueError("Report not found")

    if not is_superuser and report.reporter_id != current_user_id:
        raise PermissionError("Not allowed to delete this report")

    await db.delete(report)
    await db.commit()
