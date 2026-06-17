#!/usr/bin/env bash
# Incrementally sync Cloud SQL rows into local Docker Postgres (created_at cutoff).
# CREATED_BY_AGENT
#
# TODO(!3497): Run --check-only on the VM for inty-dev and inty before prod cutover (epic #3495).
#
# Compares remote vs local row counts; for tables with created_at, copies rows where
# remote.created_at > local.max(created_at). Single-column PK tables use staging +
# ON CONFLICT DO NOTHING to tolerate re-runs. Updates chat_history_id_seq when needed.
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
#   APPLY_MAX_PASSES        default 5 (apply mode retries until all tables match)

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

CLOUDSQL_HOST="${CLOUDSQL_HOST:-10.41.177.3}"
LOCAL_PG_HOST="${LOCAL_PG_HOST:-localhost}"
LOCAL_PG_PORT="${LOCAL_PG_PORT:-5432}"
PGUSER="${PGUSER:-postgres}"
APPLY_MAX_PASSES="${APPLY_MAX_PASSES:-5}"

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
  psql_remote -At -c "
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

get_pk_columns() {
  local tbl="$1"
  psql_local -At -c "
    SELECT a.attname
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_index i ON i.indrelid = c.oid AND i.indisprimary
    JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = ANY(i.indkey) AND NOT a.attisdropped
    WHERE n.nspname = 'public'
      AND c.relname = '${tbl}'
    ORDER BY array_position(i.indkey, a.attnum);
  "
}

# Parent tables first so FK-dependent rows can insert. TODO: derive order from FK graph.
SYNC_TABLE_PRIORITY=(users agents chats user_subscriptions resources)

table_sync_priority() {
  local tbl="$1"
  local i
  for i in "${!SYNC_TABLE_PRIORITY[@]}"; do
    if [[ "${tbl}" == "${SYNC_TABLE_PRIORITY[$i]}" ]]; then
      printf '%03d' "$i"
      return
    fi
  done
  printf '999_%s' "${tbl}"
}

sort_mismatched_for_apply() {
  local -n _tables_ref="$1"
  local sorted=()
  local tbl
  mapfile -t sorted < <(
    for tbl in "${_tables_ref[@]}"; do
      echo "$(table_sync_priority "${tbl}") ${tbl}"
    done | sort | awk '{print $2}'
  )
  _tables_ref=("${sorted[@]}")
}

join_quoted_column_identifiers() {
  local col quoted result=""
  for col in "$@"; do
    col="${col//\"/\"\"}"
    quoted="\"${col}\""
    if [[ -n "${result}" ]]; then
      result+=","
    fi
    result+="${quoted}"
  done
  echo "${result}"
}

import_csv_to_table() {
  local tbl="$1"
  local csv_path="$2"
  local quoted_cols="$3"
  local -a pk_cols=()

  mapfile -t pk_cols < <(get_pk_columns "${tbl}")

  if [[ ${#pk_cols[@]} -eq 1 ]]; then
    local quoted_pk
    quoted_pk="$(join_quoted_column_identifiers "${pk_cols[0]}")"
    psql_local -v ON_ERROR_STOP=1 <<SQL
CREATE TEMP TABLE sync_incr_staging (LIKE public."${tbl}" INCLUDING ALL) ON COMMIT DROP;
\\copy sync_incr_staging (${quoted_cols}) FROM '${csv_path}' WITH (FORMAT csv, HEADER true)
INSERT INTO public."${tbl}" SELECT ${quoted_cols} FROM sync_incr_staging ON CONFLICT (${quoted_pk}) DO NOTHING;
SQL
  else
    psql_local -c "\\copy public.\"${tbl}\" (${quoted_cols}) FROM '${csv_path}' WITH (FORMAT csv, HEADER true)"
  fi
}

sync_table_incremental() {
  local tbl="$1"
  local cutoff cols quoted_cols csv_path row_count

  cutoff="$(local_max_created_at "${tbl}")"
  mapfile -t cols < <(list_column_names "${tbl}")
  quoted_cols="$(join_quoted_column_identifiers "${cols[@]}")"

  csv_path="${TMP_DIR}/${tbl}.csv"
  psql_remote -c "\\copy (SELECT ${quoted_cols} FROM public.\"${tbl}\" WHERE created_at > '${cutoff}' ORDER BY created_at) TO '${csv_path}' WITH (FORMAT csv, HEADER true)"

  row_count=$(( $(wc -l < "${csv_path}") - 1 ))
  if [[ "${row_count}" -le 0 ]]; then
    echo "  ${tbl}: nothing to copy (cutoff ${cutoff})"
    return 0
  fi

  import_csv_to_table "${tbl}" "${csv_path}" "${quoted_cols}"
  echo "  ${tbl}: copied ${row_count} row(s) (cutoff ${cutoff})"

  if [[ "${tbl}" == "chat_history" ]]; then
    psql_local -c "SELECT setval('chat_history_id_seq', (SELECT COALESCE(max(id), 1) FROM public.chat_history));"
    echo "  chat_history: updated chat_history_id_seq"
  fi
}

collect_mismatches() {
  local -n _mismatched_ref="$1"
  local -n _skipped_ref="$2"
  local tbl remote_count local_count delta

  _mismatched_ref=()
  _skipped_ref=()

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
      _skipped_ref+=("${tbl}")
      continue
    fi
    if [[ -z "$(table_has_created_at "${tbl}")" ]]; then
      echo "  skip: no created_at column; use full pg_dump/pg_restore in LOCAL_POSTGRES.md"
      _skipped_ref+=("${tbl}")
      continue
    fi
    _mismatched_ref+=("${tbl}")
  done < <(list_public_tables)
}

report_sync_status() {
  local mismatched=()
  local skipped=()

  collect_mismatches mismatched skipped

  if [[ ${#mismatched[@]} -eq 0 ]]; then
    if [[ ${#skipped[@]} -eq 0 ]]; then
      echo "All public tables match."
    else
      echo "No incrementally syncable mismatches."
    fi
    return 0
  fi

  return 2
}

apply_incremental_sync() {
  local pass mismatched=()
  local skipped=()

  for (( pass = 1; pass <= APPLY_MAX_PASSES; pass++ )); do
    collect_mismatches mismatched skipped
    if [[ ${#mismatched[@]} -eq 0 ]]; then
      echo "All public tables match after pass ${pass}."
      return 0
    fi

    echo
    echo "Applying incremental sync (pass ${pass}/${APPLY_MAX_PASSES})..."
    sort_mismatched_for_apply mismatched
    local tbl
    for tbl in "${mismatched[@]}"; do
      sync_table_incremental "${tbl}"
    done
  done

  collect_mismatches mismatched skipped
  if [[ ${#mismatched[@]} -gt 0 ]]; then
    echo "Sync incomplete after ${APPLY_MAX_PASSES} pass(es); re-run --apply or use full pg_dump/pg_restore." >&2
    return 1
  fi
}

main() {
  parse_args "$@"
  load_password
  TMP_DIR="$(mktemp -d)"

  echo "Cloud SQL ${CLOUDSQL_HOST}/${DB} -> local ${LOCAL_PG_HOST}:${LOCAL_PG_PORT}/${DB} (${MODE})"
  echo

  if [[ "${MODE}" == "check" ]]; then
    if report_sync_status; then
      exit 0
    fi
    echo
    echo "Run with --apply to copy rows where created_at > local.max(created_at)."
    exit 2
  fi

  apply_incremental_sync
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
