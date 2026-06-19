#!/usr/bin/env bash
# Idempotent Cloud Agent "update" step: system tools + Python venv + deps + default config.yaml.
# Runs from repository root (Cursor contract). Postgres is started in cloud-agent-start.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

bash "${ROOT}/.cursor/cloud-agent-apt.sh"

if [[ ! -d .venv ]]; then
  python3.12 -m venv .venv
fi

# shellcheck source=/dev/null
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -r requirements.txt -r tests/requirements.txt

# pyproject.toml [dependency-groups].dev — install into .venv (additive).
# Do not run `uv sync --group dev` here: pyproject has no runtime deps, so sync would replace the app venv.
python -m pip install 'uv>=0.9' 'black>=24' 'pylint>=3.2' 'ruff>=0.9' 'vulture>=2.14'

# TODO(INTY_CONFIG_YAML): export INTY_CONFIG_YAML=devops/config.yaml.test instead of cp
if [[ ! -f config.yaml ]]; then
  cp devops/config.yaml.test config.yaml
fi

# TODO(INTY_CLOUD_AGENT_ANDROID): move Android SDK / AVD setup from dashboard snapshot into install or cloud-agent-android.sh
