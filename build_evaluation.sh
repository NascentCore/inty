#!/bin/bash -e

# 构建 inty_sdk
echo "📦 构建 inty_sdk..."
pushd evaluation/inty_sdk
yarn install # Install dependencies for inty_sdk
yarn run build # Build inty_sdk, which should create its dist folder
popd

# 构建 inty-eval 前端，并将其拷贝到 python server 静态资源目录
pushd evaluation

# 安装依赖（在Docker环境中总是重新安装以确保架构兼容性）
echo "📦 安装前端依赖..."
npm install

# 构建前端（不设置环境变量，使用相对路径）
echo "🔨 构建前端应用..."
npm run build

popd

# 部署到后端静态目录
echo "📁 部署到后端静态目录..."
rm -rf app/static/evaluation
mkdir -p app/static/evaluation
cp -r evaluation/dist/* app/static/evaluation/
cp -r evaluation/resources/ app/static/evaluation/resources/

echo "✅ 构建和部署完成！"
echo "🌐 访问地址: http://127.0.0.1:8000/evaluation"
