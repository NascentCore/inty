#!/bin/bash
# 测试 nginx 配置文件的辅助脚本
# 用法: ./test_nginx.sh [配置文件路径]
# 默认: devops/nginx.conf

CONFIG_FILE="${1:-devops/nginx.conf}"
TEST_CONFIG="/tmp/nginx_test.conf"

# 创建临时测试配置文件，包装在 http {} 块中
cat > "$TEST_CONFIG" << 'EOF'
# 测试配置文件，仅用于语法检查
events {
    worker_connections 1024;
}

http {
EOF

# 追加实际配置文件内容
cat "$CONFIG_FILE" >> "$TEST_CONFIG"

# 关闭 http 块
echo "}" >> "$TEST_CONFIG"

# 测试配置
echo "正在测试配置文件: $CONFIG_FILE"
echo "临时测试文件: $TEST_CONFIG"
echo ""

if command -v nginx &> /dev/null; then
    nginx -t -c "$TEST_CONFIG"
    EXIT_CODE=$?
    
    # 清理临时文件
    rm -f "$TEST_CONFIG"
    
    exit $EXIT_CODE
else
    echo "错误: 未找到 nginx 命令"
    echo "请确保 nginx 已安装并在 PATH 中"
    rm -f "$TEST_CONFIG"
    exit 1
fi

