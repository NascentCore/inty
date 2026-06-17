"""Tests for sync_cloudsql_inty_incremental.sh column identifier quoting."""

import re
import subprocess
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parent / "scripts" / "sync_cloudsql_inty_incremental.sh"
CONFIG_PROD = Path(__file__).parent / "config.yaml.prod"


def join_quoted_column_identifiers(*columns: str) -> str:
    """Run join_quoted_column_identifiers from the sync script (source-safe)."""
    args = " ".join(subprocess.list2cmdline([col]) for col in columns)
    completed = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{SCRIPT_PATH}"; join_quoted_column_identifiers {args}',
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.rstrip("\n")


def read_local_pg_password() -> str | None:
    text = CONFIG_PROD.read_text(encoding="utf-8")
    match = re.search(
        r"^database:\s*\n(?:[ \t]+.*\n)*?[ \t]+password:[ \t]*\"?([^\"#\n]+)\"?",
        text,
        re.MULTILINE,
    )
    return match.group(1) if match else None


def test_old_unquoted_column_list_lacks_quotes():
    """Reproduce bug: comma-joined names break on PostgreSQL reserved words."""
    cols = ["id", "user", "date", "created_at"]
    col_list = ",".join(cols)
    copy_cols = ",".join(cols)
    assert col_list == "id,user,date,created_at"
    assert copy_cols == "id,user,date,created_at"
    assert '"user"' not in col_list


def test_join_quoted_column_identifiers_reserved_words():
    assert join_quoted_column_identifiers("id", "date", "user", "group", "created_at") == (
        '"id","date","user","group","created_at"'
    )


def test_join_quoted_column_identifiers_escapes_embedded_quotes():
    assert join_quoted_column_identifiers('col"name') == '"col""name"'


@pytest.mark.parametrize(
    ("columns", "expected"),
    [
        (("id",), '"id"'),
        ((), ""),
    ],
)
def test_join_quoted_column_identifiers_edge_cases(columns: tuple[str, ...], expected: str):
    assert join_quoted_column_identifiers(*columns) == expected


def test_unquoted_select_misreads_user_column():
    """PostgreSQL treats bare user as current_user(), not the column."""
    password = read_local_pg_password()
    if password is None:
        pytest.skip("could not read database.password from config.yaml.prod")

    sql = """
CREATE TEMP TABLE sync_quote_bug_demo (
  id int,
  "user" text,
  created_at timestamptz DEFAULT now()
);
INSERT INTO sync_quote_bug_demo (id, "user") VALUES (1, 'row-user');
SELECT user FROM sync_quote_bug_demo LIMIT 1;
"""
    completed = subprocess.run(
        ["psql", "-h", "localhost", "-U", "postgres", "-d", "postgres", "-At", "-c", sql],
        capture_output=True,
        text=True,
        env={"PGPASSWORD": password},
    )
    if completed.returncode != 0:
        pytest.skip(f"local postgres unavailable: {completed.stderr.strip()}")

    assert completed.stdout.strip() == "postgres"

    quoted_sql = """
CREATE TEMP TABLE sync_quote_bug_demo (
  id int,
  "user" text,
  created_at timestamptz DEFAULT now()
);
INSERT INTO sync_quote_bug_demo (id, "user") VALUES (1, 'row-user');
SELECT "user" FROM sync_quote_bug_demo LIMIT 1;
"""
    completed = subprocess.run(
        ["psql", "-h", "localhost", "-U", "postgres", "-d", "postgres", "-At", "-c", quoted_sql],
        check=True,
        capture_output=True,
        text=True,
        env={"PGPASSWORD": password},
    )
    assert completed.stdout.strip() == "row-user"
