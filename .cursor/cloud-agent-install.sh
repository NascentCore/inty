#!/usr/bin/env bash
# Idempotent Cloud Agent "update" step: Python venv + deps + default config.yaml.
# Runs from repository root (Cursor contract). Postgres is started in cloud-agent-start.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

need_apt=
command -v python3.12 >/dev/null 2>&1 || need_apt=1
dpkg -s python3.12-venv >/dev/null 2>&1 || need_apt=1
dpkg -s python3.12-dev >/dev/null 2>&1 || need_apt=1
dpkg -s libpq-dev >/dev/null 2>&1 || need_apt=1
command -v psql >/dev/null 2>&1 || need_apt=1
command -v docker >/dev/null 2>&1 || need_apt=1

if [[ -n "${need_apt}" ]]; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq \
    python3.12 python3.12-venv python3.12-dev libpq-dev \
    postgresql postgresql-contrib docker.io
fi

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
