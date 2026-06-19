#!/usr/bin/env bash
# Idempotent Cloud Agent apt packages (Python toolchain, Postgres client, Docker, gcloud).
# Called from cloud-agent-install.sh. Runs from repository root.
set -euo pipefail

readonly GCLOUD_APT_LIST="/etc/apt/sources.list.d/google-cloud-sdk.list"
readonly GCLOUD_APT_KEYRING="/usr/share/keyrings/cloud.google.gpg"

apt_packages=()
need_apt_update=
need_gcloud_install=

add_apt_package() {
  local package="$1"
  if ! dpkg -s "${package}" >/dev/null 2>&1; then
    apt_packages+=("${package}")
    need_apt_update=1
  fi
}

if ! command -v python3.12 >/dev/null 2>&1; then
  apt_packages+=(python3.12)
  need_apt_update=1
fi

add_apt_package python3.12-venv
add_apt_package python3.12-dev
add_apt_package libpq-dev
add_apt_package postgresql
add_apt_package postgresql-contrib
add_apt_package docker.io

if ! command -v psql >/dev/null 2>&1; then
  add_apt_package postgresql
  add_apt_package postgresql-contrib
fi
if ! command -v docker >/dev/null 2>&1; then
  add_apt_package docker.io
fi

if ! command -v gcloud >/dev/null 2>&1; then
  need_gcloud_install=1
  need_apt_update=1
  add_apt_package google-cloud-cli
  add_apt_package ca-certificates
  add_apt_package gnupg
  add_apt_package curl
fi

if [[ -z "${need_apt_update}" ]]; then
  exit 0
fi

if [[ -n "${need_gcloud_install}" && ( ! -f "${GCLOUD_APT_LIST}" || ! -f "${GCLOUD_APT_KEYRING}" ) ]]; then
  curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
    | sudo gpg --dearmor -o "${GCLOUD_APT_KEYRING}"
  echo "deb [signed-by=${GCLOUD_APT_KEYRING}] https://packages.cloud.google.com/apt cloud-sdk main" \
    | sudo tee "${GCLOUD_APT_LIST}" > /dev/null
fi

sudo apt-get update -qq
if [[ ${#apt_packages[@]} -gt 0 ]]; then
  sudo apt-get install -y -qq "${apt_packages[@]}"
fi

if ! command -v python3.12 >/dev/null 2>&1; then
  echo "python3.12 missing after apt install" >&2
  exit 1
fi
if [[ -n "${need_gcloud_install}" ]] && ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud missing after apt install" >&2
  exit 1
fi
