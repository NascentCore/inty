#!/bin/bash

# 构建评测系统前端并部署到后端
# 使用方法: ./build_evaluation.sh

set -e  # 遇到错误立即退出

echo "🚀 开始构建评测系统前端..."

cd evaluation

# 安装依赖（如果需要）
if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    npm install
fi

# 构建前端
echo "🔨 构建前端应用..."
npm run build

# 部署到后端静态目录
echo "📁 部署到后端静态目录..."
mkdir -p ../app/static/evaluation
cp -r dist/* ../app/static/evaluation/

echo "✅ 构建和部署完成！"
echo "🌐 访问地址: http://127.0.0.1:8000/evaluation"
