"""Tests for local Postgres durability scripts."""

import subprocess
from pathlib import Path

import pytest

LIB_PATH = Path(__file__).parent / "scripts" / "local_postgres_lib.sh"
ENSURE_PATH = Path(__file__).parent / "scripts" / "ensure_inty_dev_postgres_container.sh"
VERIFY_PATH = Path(__file__).parent / "scripts" / "verify_local_postgres_durability.sh"
BACKUP_PATH = Path(__file__).parent / "scripts" / "backup_local_postgres.sh"
GUARD_PATH = Path(__file__).parent / "scripts" / "guard_docker_volume_prune.sh"


def read_bash_function_body(script_path: Path, function_name: str) -> str:
    """Return lines inside function_name() { ... } from a bash script."""
    lines = script_path.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"{function_name}()"))
    body: list[str] = []
    depth = 0
    for line in lines[start:]:
        depth += line.count("{") - line.count("}")
        if depth == 0 and line != lines[start]:
            break
        body.append(line)
    return "\n".join(body)


def test_lib_declares_canonical_volume_and_container():
    text = LIB_PATH.read_text(encoding="utf-8")
    assert 'readonly INTY_PG_CONTAINER="inty-dev-postgres"' in text
    assert 'readonly INTY_PG_VOLUME="inty-dev-postgres-data"' in text
    assert 'readonly INTY_PG_BACKUP_RETENTION_DAYS="14"' in text
    assert "prune_old_backups" in text
    assert "unless-stopped" not in text  # policy lives in ensure script


def test_ensure_binds_named_volume_and_restart_policy():
    text = ENSURE_PATH.read_text(encoding="utf-8")
    assert "--restart unless-stopped" in text
    assert "docker update --restart unless-stopped" in text
    assert "ensure_restart_policy" in text
    assert '-v "${INTY_PG_VOLUME}:/var/lib/postgresql/data"' in text
    assert "docker volume create" in text
    assert "INTY_PG_VOLUME_LABEL" in text
    assert "assert_canonical_mount" in text


def test_ensure_restart_policy_skips_check_only_mode():
    body = read_bash_function_body(ENSURE_PATH, "ensure_restart_policy")
    assert '"${MODE}" == "check"' in body
    assert "container_restart_policy" in body
    assert "docker update --restart unless-stopped" in body


def test_ensure_refuses_wrong_mount():
    body = read_bash_function_body(ENSURE_PATH, "assert_canonical_mount")
    assert "container_data_volume_name" in body
    assert "INTY_PG_VOLUME" in body


def test_verify_checks_restart_policy_and_volume():
    text = VERIFY_PATH.read_text(encoding="utf-8")
    assert "unless-stopped" in text
    assert "database_fingerprint" in text
    assert "VERIFY_TAG" in text
    assert "RESULT: PASS" in text


def test_verify_restart_test_compares_fingerprints():
    body = read_bash_function_body(VERIFY_PATH, "check_database_connectivity")
    assert "RESTART_TEST" in body
    assert "docker restart" in body


def test_backup_dumps_both_logical_databases():
    text = BACKUP_PATH.read_text(encoding="utf-8")
    assert "INTY_PG_DEV_DB" in text
    assert "INTY_PG_PROD_DB" in text
    assert "pg_dump" in text
    assert "docker exec" in text
    assert "prune_old_backups" in text
    assert "INTY_PG_BACKUP_RETENTION_DAYS" in text


WORKFLOW_PATH = Path(__file__).parents[1] / ".github" / "workflows" / "local_postgres_maintenance.yaml"


def test_maintenance_workflow_serializes_verify_after_backup():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "needs: backup" in text
    assert "needs.backup.result == 'skipped'" in text
    assert "devops/scripts/backup_local_postgres.sh" in text
    assert "find /opt/inty/backups/postgres" not in text


def test_guard_refuses_when_protected_volume_exists():
    text = GUARD_PATH.read_text(encoding="utf-8")
    assert "volume_exists" in text
    assert "REFUSE" in text


def test_guard_help_exits_zero():
    completed = subprocess.run(
        ["bash", str(GUARD_PATH), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "docker volume prune" in completed.stdout
