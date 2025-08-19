#!/bin/bash

# Locust 快速测试脚本 - 简化版本
# 快速测试几个关键并发数的性能表现
# 作者: Claude
# 日期: 2025-08-14

set -e

# 配置
TARGET_HOST="http://localhost:8000"
RUN_TIME="2m"
SPAWN_RATE=1

# 快速测试的并发数 (关键节点)
USER_COUNTS=(10 30 50 100)

echo "🚀 Locust 快速性能测试"
echo "目标: $TARGET_HOST"
echo "测试点: ${USER_COUNTS[*]} 并发用户"
echo "运行时间: $RUN_TIME"
echo ""

# 创建结果目录
RESULTS_DIR="quick_test_$(date +%H%M%S)"
mkdir -p "$RESULTS_DIR"

for users in "${USER_COUNTS[@]}"; do
    echo "⏳ 测试 $users 并发用户..."
    
    locust -f locustfile.py \
        --host="$TARGET_HOST" \
        --users="$users" \
        --spawn-rate="$SPAWN_RATE" \
        --run-time="$RUN_TIME" \
        --headless \
        --html="$RESULTS_DIR/report_${users}users.html" \
        --csv="$RESULTS_DIR/results_${users}users" \
        > "$RESULTS_DIR/test_${users}users.log" 2>&1
    
    # 从CSV中提取关键指标
    if [ -f "$RESULTS_DIR/results_${users}users_stats.csv" ]; then
        chat_stats=$(grep "chat_completions" "$RESULTS_DIR/results_${users}users_stats.csv" | tail -1)
        if [ -n "$chat_stats" ]; then
            IFS=',' read -ra METRICS <<< "$chat_stats"
            avg_response=${METRICS[5]}
            p95=${METRICS[15]}
            rps=${METRICS[9]}
            printf "✅ %3d 用户 - 平均: %6.0fms, P95: %6.0fms, RPS: %4.1f\n" \
                "$users" "$avg_response" "$p95" "$rps"
        fi
    else
        echo "❌ $users 用户测试失败"
    fi
done

echo ""
echo "📊 测试完成! 结果保存在: $RESULTS_DIR/"
echo "📈 查看详细报告: $RESULTS_DIR/report_*users.html"