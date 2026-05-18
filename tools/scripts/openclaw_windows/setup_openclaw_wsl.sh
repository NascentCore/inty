#!/usr/bin/env bash
set -euo pipefail

# 核心流程：安装 OpenClaw -> 校验命令可用 -> 输出 onboarding 与验收步骤。
GATEWAY_PORT="18789"
INSTALL_MODE="installer"
OPENCLAW_VERSION="latest"
OPENCLAW_GIT_DIR="${HOME}/openclaw"
DRY_RUN="false"

print_help() {
  cat <<'EOF'
Usage:
  setup_openclaw_wsl.sh [options]

Options:
  --gateway-port <port>          Gateway port used for onboarding defaults (default: 18789)
  --install-mode <mode>          installer | npm | pnpm | source (default: installer)
  --openclaw-version <version>   npm/pnpm install target, e.g. latest, beta, 2026.2.26
  --openclaw-git-dir <path>      git checkout directory for source install (default: ~/openclaw)
  --dry-run                      Print commands only, do not execute
  -h, --help                     Show this help
EOF
}

log() {
  printf '[openclaw-wsl] %s\n' "$1"
}

fail() {
  printf '[openclaw-wsl][error] %s\n' "$1" >&2
  exit 1
}

run() {
  local cmd="$1"
  if [[ "${DRY_RUN}" == "true" ]]; then
    printf '[dry-run] %s\n' "${cmd}"
    return 0
  fi
  bash -lc "${cmd}"
}

ensure_cmd() {
  local cmd_name="$1"
  if ! command -v "${cmd_name}" >/dev/null 2>&1; then
    fail "Required command not found: ${cmd_name}"
  fi
}

ensure_node_22() {
  ensure_cmd node
  local major
  major="$(node -p 'process.versions.node.split(".")[0]')"
  if [[ "${major}" -lt 22 ]]; then
    fail "Node.js 22+ is required. Current node major version: ${major}"
  fi
}

ensure_pnpm() {
  if command -v pnpm >/dev/null 2>&1; then
    return 0
  fi
  ensure_node_22
  if command -v corepack >/dev/null 2>&1; then
    run "corepack enable && corepack prepare pnpm@latest --activate"
    return 0
  fi
  run "npm install -g pnpm"
}

ensure_openclaw_path() {
  if command -v openclaw >/dev/null 2>&1; then
    return 0
  fi

  local npm_prefix
  npm_prefix="$(npm prefix -g 2>/dev/null || true)"
  if [[ -n "${npm_prefix}" && -d "${npm_prefix}/bin" ]]; then
    export PATH="${npm_prefix}/bin:${PATH}"
  fi

  if ! command -v openclaw >/dev/null 2>&1; then
    fail "openclaw command not found after install. Check global npm PATH."
  fi
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --gateway-port)
        GATEWAY_PORT="$2"
        shift 2
        ;;
      --install-mode)
        INSTALL_MODE="$2"
        shift 2
        ;;
      --openclaw-version)
        OPENCLAW_VERSION="$2"
        shift 2
        ;;
      --openclaw-git-dir)
        OPENCLAW_GIT_DIR="$2"
        shift 2
        ;;
      --dry-run)
        DRY_RUN="true"
        shift
        ;;
      -h|--help)
        print_help
        exit 0
        ;;
      *)
        fail "Unknown option: $1"
        ;;
    esac
  done
}

validate_args() {
  case "${INSTALL_MODE}" in
    installer|npm|pnpm|source) ;;
    *)
      fail "Invalid --install-mode: ${INSTALL_MODE}. Use installer|npm|pnpm|source"
      ;;
  esac

  if ! [[ "${GATEWAY_PORT}" =~ ^[0-9]+$ ]]; then
    fail "Invalid --gateway-port: ${GATEWAY_PORT}"
  fi
}

install_openclaw() {
  case "${INSTALL_MODE}" in
    installer)
      ensure_cmd curl
      log "Installing OpenClaw via install.sh"
      run "curl -fsSL --proto '=https' --tlsv1.2 https://openclaw.ai/install.sh | bash -s -- --no-onboard"
      ;;
    npm)
      ensure_node_22
      ensure_cmd npm
      log "Installing OpenClaw via npm"
      run "npm install -g openclaw@${OPENCLAW_VERSION}"
      ;;
    pnpm)
      ensure_node_22
      ensure_pnpm
      log "Installing OpenClaw via pnpm"
      run "pnpm add -g openclaw@${OPENCLAW_VERSION}"
      ;;
    source)
      ensure_node_22
      ensure_cmd git
      ensure_pnpm
      log "Installing OpenClaw from source"
      run "if [[ -d '${OPENCLAW_GIT_DIR}/.git' ]]; then cd '${OPENCLAW_GIT_DIR}' && git pull --rebase; else git clone https://github.com/openclaw/openclaw '${OPENCLAW_GIT_DIR}'; fi"
      run "cd '${OPENCLAW_GIT_DIR}' && pnpm install && pnpm ui:build && pnpm build && pnpm link --global"
      ;;
  esac
}

print_next_steps() {
  cat <<EOF

OpenClaw install step finished.

Next (interactive onboarding):
  openclaw onboard --install-daemon

Or non-interactive onboarding example (Anthropic API key):
  export ANTHROPIC_API_KEY='your-key'
  openclaw onboard --non-interactive \\
    --mode local \\
    --auth-choice apiKey \\
    --anthropic-api-key "\$ANTHROPIC_API_KEY" \\
    --secret-input-mode ref \\
    --gateway-port ${GATEWAY_PORT} \\
    --gateway-bind loopback \\
    --install-daemon \\
    --daemon-runtime node \\
    --skip-skills

Post-onboarding validation:
  openclaw doctor
  openclaw gateway status
  openclaw status --all
  openclaw dashboard
EOF
}

main() {
  parse_args "$@"
  validate_args

  log "Starting install in WSL (mode=${INSTALL_MODE}, dry_run=${DRY_RUN})"
  install_openclaw

  if [[ "${DRY_RUN}" == "false" ]]; then
    ensure_openclaw_path
    run "openclaw --version"
  fi

  print_next_steps
  log "Done."
}

main "$@"
