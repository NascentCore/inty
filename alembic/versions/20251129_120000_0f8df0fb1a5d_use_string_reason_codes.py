"""Use string reason codes for reports CREATED_BY_AGENT

Revision ID: 0f8df0fb1a5d
Revises: 6a8ac9b77c0c
Create Date: 2025-11-29 12:00:00.000000+00:00

"""
# CREATED_BY_AGENT
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.constants.report_reasons import (
    FEEDBACK_REASON_CODE_TO_ID,
    FEEDBACK_REASON_ID_TO_CODE,
    REPORT_REASON_CODE_TO_ID,
    REPORT_REASON_ID_TO_CODE,
)

# revision identifiers, used by Alembic.
revision: str = "0f8df0fb1a5d"
down_revision: Union[str, None] = "6a8ac9b77c0c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _convert_ids_to_codes(reason_ids, report_type: str):
    mapping = (
        FEEDBACK_REASON_ID_TO_CODE
        if report_type == "FEEDBACK"
        else REPORT_REASON_ID_TO_CODE
    )
    seen = set()
    codes = []
    for rid in reason_ids or []:
        code = mapping.get(rid)
        if not code or code in seen:
            continue
        seen.add(code)
        codes.append(code)
    return codes


def _convert_codes_to_ids(reason_codes, report_type: str):
    mapping = (
        FEEDBACK_REASON_CODE_TO_ID
        if report_type == "FEEDBACK"
        else REPORT_REASON_CODE_TO_ID
    )
    seen = set()
    ids = []
    for code in reason_codes or []:
        normalized = (code or "").strip().upper()
        rid = mapping.get(normalized)
        if rid is None or rid in seen:
            continue
        seen.add(rid)
        ids.append(rid)
    return ids


def upgrade() -> None:
    op.add_column(
        "report",
        sa.Column(
            "reason_codes",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
            nullable=False,
            comment="举报原因代码列表",
        ),
    )

    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, reason_ids, report_type FROM report")
    ).fetchall()
    for row in rows:
        report_type = row.report_type or "REPORT"
        codes = _convert_ids_to_codes(row.reason_ids, report_type)
        conn.execute(
            sa.text("UPDATE report SET reason_codes = :codes WHERE id = :rid"),
            {"codes": codes, "rid": row.id},
        )

    op.drop_column("report", "reason_ids")

    op.drop_index("ix_report_reason_code", table_name="report_reason")
    op.drop_table("report_reason")

    op.alter_column("report", "reason_codes", server_default=None)


def downgrade() -> None:
    op.create_table(
        "report_reason",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(
        "ix_report_reason_code", "report_reason", ["code"], unique=True
    )
    op.execute(
        sa.text(
            """
            INSERT INTO report_reason (id, code, description)
            VALUES
                (1, 'SENSITIVE_OR_SEXUAL_CONTENT', 'Sensitive or sexual content'),
                (2, 'MISINFORMATION', 'Misinformation'),
                (3, 'FRAUD_OR_SCAMS', 'Fraud or scams'),
                (4, 'VIOLATION_OF_PRIVACY', 'Violation of privacy'),
                (5, 'HARMFUL_TO_MINORS', 'Harmful to minors'),
                (6, 'VIOLATION_OF_INTELLECTUAL_PROPERTY', 'Violations of my intellectual property')
            """
        )
    )

    # 恢复旧的 ID 列
    op.add_column(
        "report",
        sa.Column(
            "reason_ids",
            postgresql.ARRAY(sa.Integer()),
            server_default="{}",
            nullable=False,
            comment="举报原因ID列表",
        ),
    )

    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, reason_codes, report_type FROM report")
    ).fetchall()
    for row in rows:
        report_type = row.report_type or "REPORT"
        reason_ids = _convert_codes_to_ids(row.reason_codes, report_type)
        conn.execute(
            sa.text("UPDATE report SET reason_ids = :ids WHERE id = :rid"),
            {"ids": reason_ids, "rid": row.id},
        )

    op.drop_column("report", "reason_codes")
    op.alter_column("report", "reason_ids", server_default=None)
