#！/bin/bash
# InTy 剧情系统负责构建脚本

set -e

echo "🎯 InTy 评测系统前端构建"
echo "=========================="
# 检查节点。js 和 npm
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请先安装 Node.js 16+"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm 未安装，请先安装 npm"
    exit 1
fi
# 显示版本信息
echo "📋 环境信息:"
echo "  Node.js: $(node --version)"
echo "  npm: $(npm --version)"
echo ""
# 进入体育系统目录
cd "$(dirname "$0")"
echo "📁 当前目录: $(pwd)"
# 安装依赖
echo "📦 安装依赖..."
npm install
# 类型检查
echo "🔍 TypeScript 类型检查..."
npm run type-check
# 代码检查
echo "🧹 ESLint 代码检查..."
npm run lint
# 构建生产版本
echo "🏗️ 构建生产版本..."
npm run build
# 检查构建结果
if [ -d "dist" ]; then
    echo "✅ 构建成功！"
    echo ""
    echo "📊 构建结果:"
    ls -la dist/
    echo ""
    echo "📁 构建文件大小:"
    du -sh dist/*
    echo ""
    echo "🌐 部署说明:"
    echo "  1. 构建文件在 ./dist/ 目录"
    echo "  2. 将 dist/ 内容复制到静态文件服务器"
    echo "  3. 或者使用 'npm run preview' 预览"
    echo ""
    echo "🚀 快速预览:"
    echo "  npm run preview"
else
    echo "❌ 构建失败，请检查错误信息"
    exit 1
fi

echo "🎉 构建完成！"