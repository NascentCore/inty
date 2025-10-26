#！/bin/bash -e
# 构建 inty_sdk
echo "📦 构建 inty_sdk..."
pushd evaluation/inty_sdk
# 由于未知原因，tsc-multi无法被yarn install安装，所以手动安装
yarn add -D tsc-multi@https://github.com/stainless-api/tsc-multi/releases/download/v1.1.9/tsc-multi.tgz
yarn install # Install dependencies for inty_sdk
yarn run build # Build inty_sdk, which should create its dist folder
popd
# 构建 inty-eval ，将其拷贝到 python 服务器静态资源目录
pushd evaluation
# 安装依赖（在Docker环境中总是重新安装以确保兼容架构）
echo "📦 安装前端依赖..."
npm install
# 构建前端（不设置环境变量，使用相对路径）
echo "🔨 构建前端应用..."
npm run build

popd
# 到静态部署目录
echo "📁 部署到后端静态目录..."
rm -rf app/static/evaluation
mkdir -p app/static/evaluation
cp -r evaluation/dist/* app/static/evaluation/
cp -r evaluation/resources/ app/static/evaluation/resources/
