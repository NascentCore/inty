#!/bin/bash

# 前端独立部署脚本

set -e

echo "🚀 开始部署 InTy 评测系统前端..."

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请先安装 Node.js 16+"
    exit 1
fi

# 检查版本
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 16 ]; then
    echo "❌ Node.js 版本过低，需要 16+，当前版本: $(node -v)"
    exit 1
fi

echo "✅ Node.js 版本检查通过: $(node -v)"

# 安装依赖
echo "📦 安装依赖..."
npm ci

# 类型检查
echo "🔍 TypeScript 类型检查..."
npm run type-check

# 代码检查
echo "🧹 代码质量检查..."
npm run lint

# 构建
echo "🏗️ 构建生产版本..."
npm run build

# 检查构建结果
if [ ! -d "dist" ] || [ ! -f "dist/index.html" ]; then
    echo "❌ 构建失败，dist 目录不存在或 index.html 缺失"
    exit 1
fi

echo "✅ 构建成功！"
echo "📁 构建文件位于: ./dist/"
echo "📊 构建统计:"
du -sh dist/
ls -la dist/

echo ""
echo "🎯 部署选项:"
echo "1. 静态服务器: npx serve dist/"
echo "2. 复制到服务器: scp -r dist/* user@server:/var/www/html/"
echo "3. 上传到 CDN: 将 dist/ 内容上传到对象存储"
echo ""
echo "🌐 本地预览: npm run preview"
echo "🎉 部署完成！"