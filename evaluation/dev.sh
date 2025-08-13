#!/bin/bash

# InTy 评测系统前端开发服务器启动脚本

set -e

echo "🎯 InTy 评测系统开发模式"
echo "========================"

# 检查后端服务
echo "🔍 检查后端服务..."
if ! curl -s http://localhost:8000/ > /dev/null; then
    echo "⚠️  后端服务未运行，请先启动:"
    echo "   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    echo ""
    echo "是否继续启动前端？(y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ 后端服务运行正常"
fi

# 进入评测系统目录
cd "$(dirname "$0")"
echo "📁 当前目录: $(pwd)"

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo "📦 安装依赖..."
    npm install
fi

echo ""
echo "🚀 启动开发服务器..."
echo "📍 前端地址: http://localhost:3000"
echo "📍 后端代理: http://localhost:3000/api -> http://localhost:8000/api"
echo "⏹️  停止服务: Ctrl+C"
echo ""

# 启动开发服务器
npm run dev