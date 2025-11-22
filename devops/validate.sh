#!/bin/bash
# nginx 配置验证脚本
# CREATED_BY_AGENT

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NGINX_CONF="${SCRIPT_DIR}/nginx.conf"

echo "验证 nginx 配置文件: ${NGINX_CONF}"

# 方法 1: 如果 nginx 已安装，使用 nginx -t
if command -v nginx &> /dev/null; then
    echo "使用 nginx -t 验证..."
    # 注意：如果这是 server 块片段，需要指定完整的主配置文件路径
    # 或者使用 -p 指定 prefix 路径
    if nginx -t -c "${NGINX_CONF}" 2>&1; then
        echo "✓ 配置验证通过"
        exit 0
    else
        echo "✗ 配置验证失败"
        exit 1
    fi
fi

# 方法 2: 使用 Docker 运行 nginx 验证（如果 Docker 可用）
if command -v docker &> /dev/null; then
    echo "使用 Docker nginx 镜像验证..."
    # 创建临时配置文件用于验证
    TEMP_DIR=$(mktemp -d)
    trap "rm -rf ${TEMP_DIR}" EXIT
    
    # 创建最小化的 nginx 主配置，包含我们的 server 块
    cat > "${TEMP_DIR}/nginx.conf" <<EOF
events {
    worker_connections 1024;
}

http {
    include ${NGINX_CONF};
}
EOF
    
    if docker run --rm \
        -v "${TEMP_DIR}:/etc/nginx/conf.d" \
        -v "${NGINX_CONF}:/etc/nginx/conf.d/custom.conf:ro" \
        nginx:alpine \
        nginx -t -c /etc/nginx/conf.d/nginx.conf 2>&1; then
        echo "✓ 配置验证通过"
        exit 0
    else
        echo "✗ 配置验证失败"
        exit 1
    fi
fi

# 方法 3: 基本语法检查（使用 grep 检查常见错误）
echo "执行基本语法检查..."
ERRORS=0

# 检查未闭合的块
OPEN_BLOCKS=$(grep -c "{" "${NGINX_CONF}" || true)
CLOSE_BLOCKS=$(grep -c "}" "${NGINX_CONF}" || true)
if [ "${OPEN_BLOCKS}" -ne "${CLOSE_BLOCKS}" ]; then
    echo "✗ 错误：大括号不匹配 (开: ${OPEN_BLOCKS}, 闭: ${CLOSE_BLOCKS})"
    ERRORS=$((ERRORS + 1))
fi

# 检查是否有未注释的分号缺失（简单检查）
if grep -E "^\s*[^#].*[^;{}$]\s*$" "${NGINX_CONF}" | grep -vE "^\s*(server|location|if|events|http)\s*{" | grep -vE "^\s*}\s*$" | grep -vE "^\s*#"; then
    echo "⚠ 警告：可能存在缺少分号的指令（需要人工检查）"
fi

if [ "${ERRORS}" -eq 0 ]; then
    echo "✓ 基本语法检查通过"
    echo "⚠ 注意：这是基本检查，建议在服务器上使用 'nginx -t' 进行完整验证"
    exit 0
else
    echo "✗ 发现 ${ERRORS} 个错误"
    exit 1
fi

