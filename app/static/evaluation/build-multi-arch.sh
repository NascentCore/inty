#!/bin/bash

# 多架构 Docker 构建脚本

set -e

IMAGE_NAME="inty-evaluation-frontend"
TAG="${1:-latest}"

echo "🐳 多架构 Docker 构建脚本"
echo "=========================="
echo "镜像名称: $IMAGE_NAME:$TAG"
echo "支持架构: linux/amd64, linux/arm64"
echo "=========================="

# 检查 Docker Buildx
if ! docker buildx version &> /dev/null; then
    echo "❌ Docker Buildx 未安装，请升级 Docker"
    exit 1
fi

# 创建并使用 buildx builder
if ! docker buildx ls | grep -q "multi-arch-builder"; then
    echo "🔧 创建多架构构建器..."
    docker buildx create --name multi-arch-builder --use
    docker buildx inspect --bootstrap
else
    echo "✅ 使用现有构建器..."
    docker buildx use multi-arch-builder
fi

# 构建多架构镜像
echo "🏗️ 构建多架构镜像..."
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --file Dockerfile.multi-arch \
    --tag $IMAGE_NAME:$TAG \
    --push \
    .

echo "✅ 多架构镜像构建完成！"
echo ""
echo "📊 镜像信息:"
docker buildx imagetools inspect $IMAGE_NAME:$TAG

echo ""
echo "🚀 使用方法:"
echo "  docker run -d -p 3000:80 --name inty-frontend $IMAGE_NAME:$TAG"
echo ""
echo "🎉 部署完成！"