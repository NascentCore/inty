#!/usr/bin/env bash
# 从 GCP VM（SSH 别名 inty，见 devops/gcp_vm_inty_ssh_config）拉取 Docker 容器日志到本机。
# Cloud Logging（gcplogs）拉取见 devops/fetch_inty_container_logs.sh。
#
# 前置：~/.ssh/config 已包含 host inty（IdentityFile、User 等与 gcp_vm_inty_ssh_config 一致）。
#
# 用法：
#   devops/fetch_inty_vm_container_logs.sh <container|alias> [output_dir]
#
# 别名（展开为容器名）：
#   ops-dev, ops-prod, backend-dev, backend-prod,
#   push-worker-dev, push-worker-prod,
#   ops-imate-dev, ops-imate-prod, ops-imate,
#   backend-imate-dev, backend-imate-prod
#
# 环境变量：
#   INTY_SSH_HOST          SSH 别名，默认 inty
#   INTY_LOG_OUTPUT_DIR    本机输出目录，默认 <repo>/.inty/remote-logs

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly SSH_HOST="${INTY_SSH_HOST:-inty}"
readonly DEFAULT_OUTPUT_DIR="${INTY_LOG_OUTPUT_DIR:-${REPO_ROOT}/.inty/remote-logs}"

usage() {
  sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
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
    *)
      echo "未知容器或别名: ${input}" >&2
      exit 1
      ;;
  esac
}

main() {
  if [[ $# -lt 1 ]] || [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
    usage
  fi

  local container
  container="$(resolve_container_name "$1")"
  local output_dir="${2:-${DEFAULT_OUTPUT_DIR}}"
  local timestamp
  timestamp="$(date +%Y%m%d-%H%M%S)"
  local local_path="${output_dir}/${container}-${timestamp}.log"
  local remote_path
  remote_path=".inty-fetch-logs/${container}-${timestamp}.log"

  mkdir -p "${output_dir}"

  echo "SSH ${SSH_HOST}: docker logs ${container} -> ~/${remote_path}"
  ssh "${SSH_HOST}" bash -s -- "${container}" "${remote_path}" <<'REMOTE'
set -euo pipefail
container="$1"
remote_rel="$2"
remote_abs="${HOME}/${remote_rel}"
mkdir -p "$(dirname "${remote_abs}")"
if ! docker ps -a --format '{{.Names}}' | grep -Fxq "${container}"; then
  echo "远程未找到容器: ${container}" >&2
  echo "已有容器:" >&2
  docker ps -a --format '  {{.Names}}' >&2
  exit 1
fi
docker logs "${container}" >"${remote_abs}" 2>&1
wc -c <"${remote_abs}" | xargs echo "远程日志字节数:"
echo "${remote_abs}"
REMOTE

  echo "SCP -> ${local_path}"
  scp "${SSH_HOST}:${remote_path}" "${local_path}"
  ssh "${SSH_HOST}" "rm -f '${remote_path}'"

  echo "已保存: ${local_path} ($(wc -c <"${local_path}" | xargs) bytes)"
}

main "$@"
