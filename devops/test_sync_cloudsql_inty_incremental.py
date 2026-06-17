"""Tests for sync_cloudsql_inty_incremental.sh and render_vm_database_config.sh."""

import re
import subprocess
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parent / "scripts" / "sync_cloudsql_inty_incremental.sh"
RENDER_SCRIPT_PATH = Path(__file__).parent / "scripts" / "render_vm_database_config.sh"
CONFIG_PROD = Path(__file__).parent / "config.yaml.prod"


def read_bash_function_body(function_name: str) -> str:
    """Return lines inside function_name() { ... } from the sync script."""
    lines = SCRIPT_PATH.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"{function_name}()"))
    body: list[str] = []
    depth = 0
    for line in lines[start:]:
        depth += line.count("{") - line.count("}")
        if depth == 0 and line != lines[start]:
            break
        body.append(line)
    return "\n".join(body)


def run_bash_function(function_name: str, *args: str) -> str:
    """Run a sourced bash function and return stdout."""
    arg_list = " ".join(subprocess.list2cmdline([arg]) for arg in args)
    completed = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{SCRIPT_PATH}"; {function_name} {arg_list}',
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.rstrip("\n")


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


def test_render_vm_database_config_rewrites_host(tmp_path: Path):
    source = tmp_path / "config.yaml"
    dest = tmp_path / "config.vm.yaml"
    source.write_text(
        "database:\n  host: host.docker.internal\n  port: 5432\n",
        encoding="utf-8",
    )
    subprocess.run(
        [str(RENDER_SCRIPT_PATH), str(source), str(dest)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "host: localhost" in dest.read_text(encoding="utf-8")
    assert "host.docker.internal" not in dest.read_text(encoding="utf-8")


def test_table_sync_priority_orders_users_before_dependents():
    users_prio = run_bash_function("table_sync_priority", "users")
    chat_settings_prio = run_bash_function("table_sync_priority", "chat_settings")
    assert users_prio < chat_settings_prio


def test_import_csv_to_table_uses_on_conflict_for_single_pk():
    body = read_bash_function_body("import_csv_to_table")
    assert "ON CONFLICT" in body
    assert "sync_incr_staging" in body


def test_apply_incremental_sync_retries_until_match():
    body = read_bash_function_body("apply_incremental_sync")
    assert "APPLY_MAX_PASSES" in body
    assert "collect_mismatches" in body


def test_table_has_created_at_queries_remote_not_local():
    """Incremental copy filters remote rows by created_at; check must hit Cloud SQL."""
    body = read_bash_function_body("table_has_created_at")
    assert "psql_remote" in body
    assert "psql_local" not in body


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
