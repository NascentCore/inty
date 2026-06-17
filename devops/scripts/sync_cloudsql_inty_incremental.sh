#!/usr/bin/env bash
# Incrementally sync Cloud SQL rows into local Docker Postgres (created_at cutoff).
# CREATED_BY_AGENT
#
# Compares remote vs local row counts; for tables with created_at, copies rows where
# remote.created_at > local.max(created_at). Updates chat_history_id_seq when needed.
#
# Usage (from repo root):
#   devops/scripts/sync_cloudsql_inty_incremental.sh --check-only
#   devops/scripts/sync_cloudsql_inty_incremental.sh --apply
#   devops/scripts/sync_cloudsql_inty_incremental.sh --apply --db inty-dev
#
# Environment:
#   PGPASSWORD              overrides password read from devops/config.yaml.{prod,dev}
#   CLOUDSQL_HOST           default 10.41.177.3
#   LOCAL_PG_HOST           default localhost
#   LOCAL_PG_PORT           default 5432

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

CLOUDSQL_HOST="${CLOUDSQL_HOST:-10.41.177.3}"
LOCAL_PG_HOST="${LOCAL_PG_HOST:-localhost}"
LOCAL_PG_PORT="${LOCAL_PG_PORT:-5432}"
PGUSER="${PGUSER:-postgres}"

DB="inty"
MODE="check"
TMP_DIR=""

usage() {
  sed -n '2,12p' "$0" | sed 's/^# \?//'
  echo
  echo "Options:"
  echo "  --check-only   report row-count diffs (default)"
  echo "  --apply        copy incremental rows from Cloud SQL into local DB"
  echo "  --db NAME      inty (prod, default) or inty-dev"
}

cleanup() {
  if [[ -n "${TMP_DIR}" && -d "${TMP_DIR}" ]]; then
    rm -rf "${TMP_DIR}"
  fi
}
trap cleanup EXIT

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --check-only)
        MODE="check"
        shift
        ;;
      --apply)
        MODE="apply"
        shift
        ;;
      --db)
        assert_non_empty "$2" "--db requires a value"
        DB="$2"
        shift 2
        ;;
      -h | --help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage >&2
        exit 1
        ;;
    esac
  done
  case "${DB}" in
    inty | inty-dev) ;;
    *)
      echo "Unsupported --db ${DB}; use inty or inty-dev" >&2
      exit 1
      ;;
  esac
}

assert_non_empty() {
  if [[ -z "$1" ]]; then
    echo "$2" >&2
    exit 1
  fi
}

config_file_for_db() {
  case "${DB}" in
    inty) echo "${REPO_ROOT}/devops/config.yaml.prod" ;;
    inty-dev) echo "${REPO_ROOT}/devops/config.yaml.dev" ;;
  esac
}

load_password() {
  if [[ -n "${PGPASSWORD:-}" ]]; then
    return
  fi
  local cfg
  cfg="$(config_file_for_db)"
  assert_non_empty "${cfg}" "config file missing for db ${DB}"
  PGPASSWORD="$(grep -A8 '^database:' "${cfg}" | grep 'password:' | head -1 | sed -E 's/^[[:space:]]*password:[[:space:]]*"?([^"#]*)"?.*/\1/')"
  export PGPASSWORD
  assert_non_empty "${PGPASSWORD}" "could not read database.password from ${cfg}"
}

psql_remote() {
  psql -h "${CLOUDSQL_HOST}" -U "${PGUSER}" -d "${DB}" "$@"
}

psql_local() {
  psql -h "${LOCAL_PG_HOST}" -p "${LOCAL_PG_PORT}" -U "${PGUSER}" -d "${DB}" "$@"
}

list_public_tables() {
  psql_remote -At -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1;"
}

remote_row_count() {
  local tbl="$1"
  psql_remote -At -c "SELECT count(*) FROM public.\"${tbl}\";"
}

local_row_count() {
  local tbl="$1"
  psql_local -At -c "SELECT count(*) FROM public.\"${tbl}\";"
}

table_has_created_at() {
  local tbl="$1"
  psql_local -At -c "
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = '${tbl}'
      AND column_name = 'created_at'
    LIMIT 1;
  "
}

local_max_created_at() {
  local tbl="$1"
  psql_local -At -c "SELECT COALESCE(max(created_at)::text, '-infinity') FROM public.\"${tbl}\";"
}

list_column_names() {
  local tbl="$1"
  psql_local -At -c "
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = '${tbl}'
    ORDER BY ordinal_position;
  "
}

sync_table_incremental() {
  local tbl="$1"
  local cutoff cols col_list copy_cols csv_path row_count

  cutoff="$(local_max_created_at "${tbl}")"
  mapfile -t cols < <(list_column_names "${tbl}")
  col_list="$(IFS=','; echo "${cols[*]}")"
  copy_cols="$(printf '%s,' "${cols[@]}")"
  copy_cols="${copy_cols%,}"

  csv_path="${TMP_DIR}/${tbl}.csv"
  psql_remote -c "\\copy (SELECT ${col_list} FROM public.\"${tbl}\" WHERE created_at > '${cutoff}' ORDER BY created_at) TO '${csv_path}' WITH (FORMAT csv, HEADER true)"

  row_count=$(( $(wc -l < "${csv_path}") - 1 ))
  if [[ "${row_count}" -le 0 ]]; then
    echo "  ${tbl}: nothing to copy (cutoff ${cutoff})"
    return 0
  fi

  psql_local -c "\\copy public.\"${tbl}\" (${copy_cols}) FROM '${csv_path}' WITH (FORMAT csv, HEADER true)"
  echo "  ${tbl}: copied ${row_count} row(s) (cutoff ${cutoff})"

  if [[ "${tbl}" == "chat_history" ]]; then
    psql_local -c "SELECT setval('chat_history_id_seq', (SELECT COALESCE(max(id), 1) FROM public.chat_history));"
    echo "  chat_history: updated chat_history_id_seq"
  fi
}

main() {
  parse_args "$@"
  load_password
  TMP_DIR="$(mktemp -d)"

  echo "Cloud SQL ${CLOUDSQL_HOST}/${DB} -> local ${LOCAL_PG_HOST}:${LOCAL_PG_PORT}/${DB} (${MODE})"
  echo

  local mismatched=()
  local skipped=()
  local tbl remote_count local_count delta

  while IFS= read -r tbl; do
    [[ -z "${tbl}" ]] && continue
    remote_count="$(remote_row_count "${tbl}")"
    local_count="$(local_row_count "${tbl}")"
    if [[ "${remote_count}" == "${local_count}" ]]; then
      continue
    fi
    delta=$((remote_count - local_count))
    echo "MISMATCH ${tbl}: remote=${remote_count} local=${local_count} delta=${delta}"
    if [[ "${delta}" -lt 0 ]]; then
      echo "  skip: local has more rows than Cloud SQL; needs manual investigation or full resync"
      skipped+=("${tbl}")
      continue
    fi
    if [[ -z "$(table_has_created_at "${tbl}")" ]]; then
      echo "  skip: no created_at column; use full pg_dump/pg_restore in LOCAL_POSTGRES.md"
      skipped+=("${tbl}")
      continue
    fi
    mismatched+=("${tbl}")
  done < <(list_public_tables)

  if [[ ${#mismatched[@]} -eq 0 ]]; then
    if [[ ${#skipped[@]} -eq 0 ]]; then
      echo "All public tables match."
    else
      echo "No incrementally syncable mismatches."
    fi
    exit 0
  fi

  if [[ "${MODE}" == "check" ]]; then
    echo
    echo "Run with --apply to copy rows where created_at > local.max(created_at)."
    exit 2
  fi

  echo
  echo "Applying incremental sync..."
  for tbl in "${mismatched[@]}"; do
    sync_table_incremental "${tbl}"
  done

  echo
  echo "Post-sync verification:"
  local ok=true
  for tbl in "${mismatched[@]}"; do
    remote_count="$(remote_row_count "${tbl}")"
    local_count="$(local_row_count "${tbl}")"
    if [[ "${remote_count}" != "${local_count}" ]]; then
      echo "STILL MISMATCH ${tbl}: remote=${remote_count} local=${local_count}"
      ok=false
    else
      echo "OK ${tbl}: ${local_count} rows"
    fi
  done

  if [[ "${ok}" != true ]]; then
    exit 1
  fi
}

main "$@"
