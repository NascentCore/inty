#!/usr/bin/env bash
# 从 GCP Cloud Logging（Docker gcplogs）拉取容器 stdout 到本机。
#
# 使用 jsonPayload.container.name 过滤；时间窗用 timestamp>= 显式过滤（--freshness 仅在 --order=desc 时生效）。
#
# 前置：gcloud 已登录且可访问项目（默认 alien-paratext-461204-i9）。
#
# 用法：
#   devops/fetch_inty_container_logs.sh <container|alias> <hours_ago> [output_dir]
#
# 示例：
#   devops/fetch_inty_container_logs.sh ops-dev 24
#   devops/fetch_inty_container_logs.sh inty-ops-prod 6 .inty/remote-logs
#
# 别名（与 fetch_inty_vm_container_logs.sh 一致）：
#   ops-dev, ops-prod, backend-dev, backend-prod,
#   push-worker-dev, push-worker-prod,
#   ops-imate-dev, ops-imate-prod, ops-imate,
#   backend-imate-dev, backend-imate-prod
#
# 环境变量：
#   INTY_GCP_PROJECT       GCP 项目 ID，默认 alien-paratext-461204-i9
#   INTY_LOG_OUTPUT_DIR    输出目录，默认 <repo>/.inty/remote-logs
#   INTY_GCLOUD_LOG_LIMIT  单次 read 上限，默认 50000

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly GCP_PROJECT="${INTY_GCP_PROJECT:-alien-paratext-461204-i9}"
readonly DEFAULT_OUTPUT_DIR="${INTY_LOG_OUTPUT_DIR:-${REPO_ROOT}/.inty/remote-logs}"
readonly GCLOUD_LOG_LIMIT="${INTY_GCLOUD_LOG_LIMIT:-50000}"

usage() {
  sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
}

resolve_container_name() {
  local input="$1"
  case "${input}" in
    ops-dev) echo "inty-ops-dev" ;;
    ops-prod) echo "inty-ops-prod" ;;
    backend-dev) echo "inty-backend-dev" ;;
    backend-prod) echo "inty-backend-prod" ;;
    push-worker-dev) echo "inty-push-worker-dev" ;;
    push-worker-prod) echo "inty-push-worker-prod" ;;
    ops-imate-dev) echo "inty-ops-imate-dev" ;;
    ops-imate-prod) echo "inty-ops-imate-prod" ;;
    ops-imate) echo "inty-ops-imate" ;;
    backend-imate-dev) echo "inty-backend-imate-dev" ;;
    backend-imate-prod) echo "inty-backend-imate-prod" ;;
    inty-*) echo "${input}" ;;
    /*) echo "${input#/}" ;;
    *)
      echo "未知容器或别名: ${input}" >&2
      exit 1
      ;;
  esac
}

# gcplogs 写入 Cloud Logging 时 container.name 带前导 /
gcp_container_json_name() {
  local docker_name="$1"
  echo "/${docker_name}"
}

timestamp_hours_ago_utc() {
  local hours="$1"
  case "$(uname -s)" in
    Darwin) date -u -v-"${hours}"H '+%Y-%m-%dT%H:%M:%SZ' ;;
    *) date -u -d "${hours} hours ago" '+%Y-%m-%dT%H:%M:%SZ' ;;
  esac
}

main() {
  if [[ $# -lt 2 ]] || [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
    usage
  fi

  local hours_ago="$2"
  if ! [[ "${hours_ago}" =~ ^[0-9]+$ ]] || [[ "${hours_ago}" -lt 1 ]]; then
    echo "hours_ago 须为正整数，收到: ${hours_ago}" >&2
    exit 1
  fi

  if ! command -v gcloud >/dev/null 2>&1; then
    echo "未找到 gcloud，请先安装并 gcloud auth login" >&2
    exit 1
  fi

  local container
  container="$(resolve_container_name "$1")"
  local gcp_container
  gcp_container="$(gcp_container_json_name "${container}")"
  local output_dir="${3:-${DEFAULT_OUTPUT_DIR}}"
  local ts_start
  ts_start="$(timestamp_hours_ago_utc "${hours_ago}")"
  local timestamp
  timestamp="$(date -u '+%Y%m%d-%H%M%S')"
  local local_path="${output_dir}/${container}-gcp-${hours_ago}h-${timestamp}.log"
  local log_filter
  log_filter="jsonPayload.container.name=\"${gcp_container}\" AND timestamp>=\"${ts_start}\""

  mkdir -p "${output_dir}"

  echo "project=${GCP_PROJECT}"
  echo "filter=${log_filter}"
  echo "limit=${GCLOUD_LOG_LIMIT} order=asc"
  echo "output=${local_path}"

  gcloud logging read "${log_filter}" \
    --project="${GCP_PROJECT}" \
    --order=asc \
    --limit="${GCLOUD_LOG_LIMIT}" \
    --format='value(timestamp,severity,jsonPayload.message)' \
    >"${local_path}"

  local line_count
  line_count="$(wc -l <"${local_path}" | tr -d ' ')"
  echo "已保存: ${local_path} (${line_count} 行)"

  if [[ "${line_count}" -ge "${GCLOUD_LOG_LIMIT}" ]]; then
    echo "警告: 行数达到 limit=${GCLOUD_LOG_LIMIT}，可能未包含完整 ${hours_ago}h 窗口；请缩小 hours 或提高 INTY_GCLOUD_LOG_LIMIT 后重试" >&2
  fi
}

main "$@"
