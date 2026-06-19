"""Tests for local Postgres durability scripts."""

import subprocess
from pathlib import Path

import pytest

LIB_PATH = Path(__file__).parent / "scripts" / "local_postgres_lib.sh"
ENSURE_PATH = Path(__file__).parent / "scripts" / "ensure_inty_dev_postgres_container.sh"
VERIFY_PATH = Path(__file__).parent / "scripts" / "verify_local_postgres_durability.sh"
BACKUP_PATH = Path(__file__).parent / "scripts" / "backup_local_postgres.sh"
GUARD_PATH = Path(__file__).parent / "scripts" / "guard_docker_volume_prune.sh"
CONFIG_DEV = Path(__file__).parent / "config.yaml.dev"
CONFIG_PROD = Path(__file__).parent / "config.yaml.prod"


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
    assert 'readonly INTY_PG_CONTAINER="inty-pg"' in text
    assert 'readonly INTY_PG_CONTAINER_LEGACY="inty-dev-postgres"' in text
    assert 'readonly INTY_PG_VOLUME="inty-dev-postgres-data"' in text
    assert 'readonly INTY_PG_MAJOR_VERSION="17"' in text
    assert 'readonly INTY_PG_IMAGE="pgvector/pgvector:pg17"' in text
    assert 'readonly INTY_PG_BACKUP_RETENTION_DAYS="14"' in text
    assert "prune_old_backups" in text
    assert "postgres_server_version_major" in text
    assert "assert_dev_prod_database_server_credentials_match" in text
    assert "align_postgres_superuser_password" in text
    assert "postgres_host_auth_works" in text
    assert "finalize_postgres_instance_access" in text
    assert "sql_escape_pg_literal" in text
    assert "unless-stopped" not in text  # policy lives in ensure script


def test_ensure_migrates_legacy_container_name():
    body = read_bash_function_body(LIB_PATH, "migrate_legacy_container_name")
    assert "INTY_PG_CONTAINER_LEGACY" in body
    assert "docker rename" in body
    text = ENSURE_PATH.read_text(encoding="utf-8")
    assert "migrate_legacy_container_name" in text


def test_dev_prod_configs_share_server_credentials():
    completed = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{LIB_PATH}"; assert_dev_prod_database_server_credentials_match',
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_backup_asserts_shared_server_credentials():
    text = BACKUP_PATH.read_text(encoding="utf-8")
    assert "assert_dev_prod_database_server_credentials_match" in text
    assert "INTY_PG_USER" in text


def test_ensure_binds_named_volume_and_restart_policy():
    text = ENSURE_PATH.read_text(encoding="utf-8")
    assert "--restart unless-stopped" in text
    assert "docker update --restart unless-stopped" in text
    assert "ensure_restart_policy" in text
    assert "assert_image_matches_canonical" in text
    assert "--recreate" in text
    assert "finalize_postgres_instance_access" in text
    assert "assert_dev_prod_database_server_credentials_match" in text
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
    assert "check_server_version" in text
    assert "INTY_PG_MAJOR_VERSION" in text
    assert "assert_dev_prod_database_server_credentials_match" in text
    assert "VERIFY_TAG" in text
    assert "RESULT: PASS" in text


def test_verify_restart_test_compares_fingerprints():
    body = read_bash_function_body(VERIFY_PATH, "check_database_connectivity")
    assert "RESTART_TEST" in body
    assert "docker restart" in body
    assert "finalize_postgres_instance_access" in body


def test_backup_dumps_both_logical_databases():
    text = BACKUP_PATH.read_text(encoding="utf-8")
    assert "INTY_PG_DEV_DB" in text
    assert "INTY_PG_PROD_DB" in text
    assert "pg_dump" in text
    assert "docker exec" in text
    assert "prune_old_backups" in text
    assert "INTY_PG_BACKUP_RETENTION_DAYS" in text


def test_finalize_aligns_password_only_when_host_auth_fails():
    body = read_bash_function_body(LIB_PATH, "finalize_postgres_instance_access")
    assert "postgres_host_auth_works" in body
    assert "align_postgres_superuser_password" in body
    text = BACKUP_PATH.read_text(encoding="utf-8")
    assert "assert_dev_prod_database_server_credentials_match" in text
    assert "INTY_PG_USER" in text


def test_sql_escape_pg_literal_doubles_single_quotes():
    completed = subprocess.run(
        [
            "bash",
            "-c",
            'source "' + str(LIB_PATH) + "\"; sql_escape_pg_literal \"a'b\"",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout == "a''b"


WORKFLOW_PATH = Path(__file__).parents[1] / ".github" / "workflows" / "local_postgres_maintenance.yaml"
BACKEND_DEPLOY_WORKFLOW_PATH = (
    Path(__file__).parents[1] / ".github" / "workflows" / "build_and_deploy_backend.yml"
)


def test_maintenance_workflow_serializes_verify_after_backup():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "needs: backup" in text
    assert "needs.backup.result == 'skipped'" in text
    assert "devops/scripts/backup_local_postgres.sh" in text
    assert "find /opt/inty/backups/postgres" not in text


def test_backend_deploy_workflow_ensures_inty_pg_and_host_gateway():
    text = BACKEND_DEPLOY_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "devops/config.yaml.prod" in text
    assert "logical_db=inty" in text
    assert "Assert baked config targets VM inty-pg" in text
    assert 'host: "host.docker.internal"' in text
    assert "Ensure inty-pg before deploy" in text
    assert "ensure_inty_dev_postgres_container.sh" in text
    assert "docker exec inty-pg psql" in text
    assert "host.docker.internal:host-gateway" in text


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
