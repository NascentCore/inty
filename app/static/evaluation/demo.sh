#!/bin/bash

# InTy 评测系统完整演示脚本

set -e

echo "🎯 InTy 评测系统 - 完整演示"
echo "================================"
echo ""

# 环境检查
echo "🔍 环境检查..."
echo "Node.js: $(node --version)"
echo "npm: $(npm --version)"
echo ""

# 进入评测系统目录
cd "$(dirname "$0")"
echo "📁 工作目录: $(pwd)"
echo ""

# 检查后端服务
echo "🔍 检查后端服务..."
if curl -s http://localhost:8000/ > /dev/null; then
    echo "✅ 后端服务运行正常"
else
    echo "❌ 后端服务未运行"
    echo ""
    echo "请先启动后端服务:"
    echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    echo ""
    exit 1
fi
echo ""

# 选择运行模式
echo "🎮 选择运行模式:"
echo "  1) 开发模式 (热重载，适合开发)"
echo "  2) 生产构建 (静态文件，适合部署)"
echo "  3) 仅安装依赖"
echo "  4) 查看帮助"
echo ""
read -p "请选择 (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🚀 启动开发模式..."
        echo "================================"
        
        # 检查依赖
        if [ ! -d "node_modules" ]; then
            echo "📦 安装依赖..."
            npm install
            echo ""
        fi
        
        echo "📍 前端地址: http://localhost:3000"
        echo "📍 后端代理: /api -> http://localhost:8000/api"
        echo "⏹️  停止服务: Ctrl+C"
        echo ""
        echo "✨ 特性:"
        echo "  - 热重载"
        echo "  - TypeScript 支持"
        echo "  - API 自动代理"
        echo "  - 开发工具集成"
        echo ""
        
        # 启动开发服务器
        npm run dev
        ;;
        
    2)
        echo ""
        echo "🏗️ 生产构建模式..."
        echo "================================"
        
        # 安装依赖
        if [ ! -d "node_modules" ]; then
            echo "📦 安装依赖..."
            npm install
            echo ""
        fi
        
        # TypeScript 检查
        echo "🔍 TypeScript 类型检查..."
        npm run type-check
        echo ""
        
        # 代码检查
        echo "🧹 代码质量检查..."
        npm run lint
        echo ""
        
        # 构建
        echo "🏗️ 构建生产版本..."
        npm run build
        echo ""
        
        if [ -d "dist" ]; then
            echo "✅ 构建成功！"
            echo ""
            echo "📊 构建结果:"
            ls -la dist/
            echo ""
            echo "📁 文件大小:"
            du -sh dist/*
            echo ""
            echo "🌐 部署选项:"
            echo "  1. 预览: npm run preview"
            echo "  2. 复制到后端: cp -r dist/* ../../static/evaluation/"
            echo "  3. 独立部署: npx serve dist/"
            echo ""
            
            read -p "是否启动预览服务？(y/N): " preview
            if [[ "$preview" =~ ^[Yy]$ ]]; then
                echo ""
                echo "🔍 启动预览服务..."
                echo "📍 预览地址: http://localhost:4173"
                npm run preview
            fi
        else
            echo "❌ 构建失败"
            exit 1
        fi
        ;;
        
    3)
        echo ""
        echo "📦 安装依赖..."
        echo "================================"
        npm install
        echo ""
        echo "✅ 依赖安装完成！"
        echo ""
        echo "📋 可用命令:"
        echo "  npm run dev      - 开发模式"
        echo "  npm run build    - 生产构建"
        echo "  npm run preview  - 预览构建"
        echo "  npm run lint     - 代码检查"
        echo ""
        ;;
        
    4)
        echo ""
        echo "📖 InTy 评测系统帮助"
        echo "================================"
        echo ""
        echo "🏗️ 构建选项:"
        echo "  ./dev.sh         - 快速启动开发模式"
        echo "  ./build.sh       - 快速生产构建"
        echo "  ./demo.sh        - 当前演示脚本"
        echo ""
        echo "📋 npm 命令:"
        echo "  npm run dev      - 开发服务器 (http://localhost:3000)"
        echo "  npm run build    - 生产构建到 dist/"
        echo "  npm run preview  - 预览构建结果"
        echo "  npm run lint     - ESLint 代码检查"
        echo "  npm run type-check - TypeScript 类型检查"
        echo ""
        echo "🌐 访问地址:"
        echo "  开发模式: http://localhost:3000"
        echo "  预览模式: http://localhost:4173"
        echo "  后端API:  http://localhost:8000/docs"
        echo "  简单版本: http://localhost:8000/static/evaluation/simple.html"
        echo ""
        echo "📚 文档:"
        echo "  README.md           - 完整系统文档"
        echo "  FRONTEND_SETUP.md   - 前端构建指南"
        echo "  QUICKSTART.md       - 快速启动指南"
        echo ""
        echo "🆘 故障排除:"
        echo "  1. 确保 Node.js 16+ 已安装"
        echo "  2. 确保后端服务运行在 8000 端口"
        echo "  3. 检查 3000 端口未被占用"
        echo "  4. 如有问题删除 node_modules 重新安装"
        echo ""
        ;;
        
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac