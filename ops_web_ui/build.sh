#!/bin/bash -e

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATIC_SUBDIR="ops_web_ui"

echo "🎯 构建 ops_web_ui 并同步至 app/static/${STATIC_SUBDIR}"

echo "📦 安装前端依赖..."
pushd "${SCRIPT_DIR}" >/dev/null
npm install

echo "🔨 构建前端应用..."
NODE_OPTIONS="--max-old-space-size=4096" npm run build
popd >/dev/null

echo "📁 部署到 app/static/${STATIC_SUBDIR}..."
rm -rf "${REPO_ROOT}/app/static/${STATIC_SUBDIR}"
mkdir -p "${REPO_ROOT}/app/static/${STATIC_SUBDIR}"
cp -r "${SCRIPT_DIR}/dist/." "${REPO_ROOT}/app/static/${STATIC_SUBDIR}/"

if [ -d "${SCRIPT_DIR}/resources" ]; then
  mkdir -p "${REPO_ROOT}/app/static/${STATIC_SUBDIR}/resources"
  cp -r "${SCRIPT_DIR}/resources/." "${REPO_ROOT}/app/static/${STATIC_SUBDIR}/resources/"
fi

echo "✅ 构建完成"
