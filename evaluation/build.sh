#!/bin/bash -e

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "🎯 构建 evaluation 并同步至 app/static/evaluation"

echo "📦 构建 inty_sdk..."
pushd "${SCRIPT_DIR}/inty_sdk" >/dev/null

# 先创建 dist 目录，避免 evaluation/package.json 中的 file:./inty_sdk/dist 引用失败
# 这在 CI 环境中很重要，因为 yarn 可能会检查整个工作区的依赖
mkdir -p dist
# # 创建一个临时的 package.json 占位文件，确保 dist 目录被识别为有效的包目录
# if [ ! -f dist/package.json ]; then
#   echo '{"name":"inty","version":"0.0.0"}' > dist/package.json
# fi

# tsc-multi 通过 tarball 安装，避免 yarn 解析问题
yarn add -D tsc-multi@https://github.com/stainless-api/tsc-multi/releases/download/v1.1.9/tsc-multi.tgz
yarn install
NODE_OPTIONS="--max-old-space-size=4096" yarn run build
popd >/dev/null

echo "📦 安装前端依赖..."
pushd "${SCRIPT_DIR}" >/dev/null
npm install

echo "🔍 TypeScript 类型检查..."
npm run type-check

echo "🧹 ESLint 检查..."
npm run lint

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
