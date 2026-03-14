#!/bin/bash -e

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "🎯 构建 evaluation 并同步至 app/static/evaluation"

echo "📦 安装前端依赖..."
pushd "${SCRIPT_DIR}" >/dev/null
npm install

echo "🔨 构建前端应用..."
NODE_OPTIONS="--max-old-space-size=4096" npm run build
popd >/dev/null

echo "📁 部署到 app/static/evaluation..."
rm -rf "${REPO_ROOT}/app/static/evaluation"
mkdir -p "${REPO_ROOT}/app/static/evaluation"
cp -r "${SCRIPT_DIR}/dist/." "${REPO_ROOT}/app/static/evaluation/"

if [ -d "${SCRIPT_DIR}/resources" ]; then
  mkdir -p "${REPO_ROOT}/app/static/evaluation/resources"
  cp -r "${SCRIPT_DIR}/resources/." "${REPO_ROOT}/app/static/evaluation/resources/"
fi

echo "✅ 构建完成"
