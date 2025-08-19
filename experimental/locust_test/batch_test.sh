#!/bin/bash

# Locust 批量测试脚本
# 测试不同并发用户数下的响应时间表现
# 作者: Claude
# 日期: 2025-08-14

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# 测试配置
TARGET_HOST="http://localhost:8000"
RUN_TIME="2m"
SPAWN_RATE=1
USER_COUNTS=(10 20 30 40 50 60 70 80 90 100)

# 输出目录
RESULTS_DIR="batch_test_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEST_SESSION_DIR="${RESULTS_DIR}/${TIMESTAMP}"

# 创建结果目录
mkdir -p "$TEST_SESSION_DIR"

# 汇总报告文件
SUMMARY_FILE="${TEST_SESSION_DIR}/batch_test_summary.txt"

# 显示帮助信息
show_help() {
    echo "Locust 批量测试脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help          显示帮助信息"
    echo "  --host HOST         目标主机 (默认: http://localhost:8000)"
    echo "  --run-time TIME     测试运行时间 (默认: 2m)"
    echo "  --spawn-rate N      用户启动速率 (默认: 1)"
    echo "  --users 'N1,N2,N3'  自定义用户数序列 (默认: 10,20,30...100)"
    echo ""
    echo "示例:"
    echo "  $0                                    # 使用默认配置"
    echo "  $0 --host http://192.168.1.100:8000  # 指定目标主机"
    echo "  $0 --run-time 5m --spawn-rate 2     # 自定义参数"
    echo "  $0 --users '5,15,25,50'              # 自定义用户数序列"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v locust &> /dev/null; then
        log_error "Locust 未安装或不在PATH中"
        log_info "安装方法: pip install locust"
        exit 1
    fi
    
    if [ ! -f "locustfile.py" ]; then
        log_error "找不到 locustfile.py 文件"
        log_error "请确保在正确的目录中运行此脚本"
        exit 1
    fi
    
    log_info "依赖检查通过"
}

# 测试目标主机连通性
test_connectivity() {
    log_info "测试目标主机连通性..."
    
    if curl -f -s --connect-timeout 5 "${TARGET_HOST}/health" > /dev/null 2>&1; then
        log_info "目标主机连通性正常: $TARGET_HOST"
    else
        log_warn "无法连接到目标主机: $TARGET_HOST"
        log_warn "请确保服务已启动并可访问"
        read -p "是否继续测试? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# 执行单个测试
run_single_test() {
    local users=$1
    local test_start_time=$(date)
    
    log_info "开始测试: $users 并发用户, $RUN_TIME 运行时间"
    
    # 文件名
    local html_report="${TEST_SESSION_DIR}/report_${users}users.html"
    local csv_prefix="${TEST_SESSION_DIR}/results_${users}users"
    local log_file="${TEST_SESSION_DIR}/test_${users}users.log"
    
    # 执行 Locust 测试
    local cmd="locust -f locustfile.py --host=$TARGET_HOST --users=$users --spawn-rate=$SPAWN_RATE --run-time=$RUN_TIME --headless --html=$html_report --csv=$csv_prefix"
    
    log_debug "执行命令: $cmd"
    
    # 记录开始时间
    local start_timestamp=$(date +%s)
    
    # 运行测试并捕获输出
    if $cmd > "$log_file" 2>&1; then
        local end_timestamp=$(date +%s)
        local duration=$((end_timestamp - start_timestamp))
        local test_end_time=$(date)
        
        log_info "测试完成: $users 用户 (耗时: ${duration}秒)"
        
        # 从CSV文件中提取关键指标
        extract_metrics "$users" "$csv_prefix" "$duration" "$test_start_time" "$test_end_time"
    else
        log_error "测试失败: $users 用户"
        log_error "详细错误请查看: $log_file"
        return 1
    fi
}

# 从CSV结果中提取关键指标
extract_metrics() {
    local users=$1
    local csv_prefix=$2
    local duration=$3
    local start_time="$4"
    local end_time="$5"
    
    local stats_file="${csv_prefix}_stats.csv"
    local distribution_file="${csv_prefix}_stats_history.csv"
    
    if [ -f "$stats_file" ]; then
        # 提取聊天接口的统计数据（跳过标题行）
        local chat_stats=$(grep "chat_completions" "$stats_file" | tail -1)
        
        if [ -n "$chat_stats" ]; then
            # CSV格式: Type,Name,Request Count,Failure Count,Median Response Time,Average Response Time,Min Response Time,Max Response Time,Average Content Size,Requests/s,Failures/s,50%,66%,75%,80%,90%,95%,98%,99%,99.9%,99.99%,100%
            IFS=',' read -ra METRICS <<< "$chat_stats"
            
            local request_count=${METRICS[2]}
            local failure_count=${METRICS[3]}
            local avg_response=${METRICS[5]}
            local min_response=${METRICS[6]}
            local max_response=${METRICS[7]}
            local rps=${METRICS[9]}
            local p95=${METRICS[15]}
            local p99=${METRICS[17]}
            
            # 写入汇总报告
            cat >> "$SUMMARY_FILE" << EOF
=== $users 并发用户测试结果 ===
测试时间: $start_time - $end_time
测试耗时: ${duration}秒
请求总数: $request_count
失败次数: $failure_count
平均响应时间: ${avg_response}ms
最小响应时间: ${min_response}ms
最大响应时间: ${max_response}ms
P95响应时间: ${p95}ms
P99响应时间: ${p99}ms
每秒请求数: $rps
成功率: $(echo "scale=2; (($request_count - $failure_count) * 100) / $request_count" | bc -l)%

EOF
        else
            log_warn "未能提取 $users 用户的聊天接口统计数据"
        fi
    else
        log_warn "未找到统计文件: $stats_file"
    fi
}

# 生成最终汇总报告
generate_final_summary() {
    log_info "生成最终汇总报告..."
    
    local final_summary="${TEST_SESSION_DIR}/performance_analysis.txt"
    
    cat > "$final_summary" << EOF
# Locust 批量性能测试分析报告

## 测试配置
- 目标主机: $TARGET_HOST
- 运行时间: $RUN_TIME
- 用户启动速率: $SPAWN_RATE
- 测试用户数: ${USER_COUNTS[*]}
- 测试时间: $(date)

## 测试结果汇总

EOF
    
    # 创建性能对比表格
    cat >> "$final_summary" << EOF
| 并发数 | 平均响应时间(ms) | P95响应时间(ms) | P99响应时间(ms) | RPS | 成功率 |
|--------|------------------|-----------------|-----------------|-----|--------|
EOF
    
    # 从汇总文件中提取数据生成表格
    for users in "${USER_COUNTS[@]}"; do
        local csv_file="${TEST_SESSION_DIR}/results_${users}users_stats.csv"
        if [ -f "$csv_file" ]; then
            local chat_stats=$(grep "chat_completions" "$csv_file" | tail -1)
            if [ -n "$chat_stats" ]; then
                IFS=',' read -ra METRICS <<< "$chat_stats"
                local request_count=${METRICS[2]}
                local failure_count=${METRICS[3]}
                local avg_response=${METRICS[5]}
                local rps=${METRICS[9]}
                local p95=${METRICS[15]}
                local p99=${METRICS[17]}
                local success_rate=$(echo "scale=1; (($request_count - $failure_count) * 100) / $request_count" | bc -l)
                
                printf "| %6d | %14.1f | %13.1f | %13.1f | %3.1f | %5.1f%% |\n" \
                    "$users" "$avg_response" "$p95" "$p99" "$rps" "$success_rate" >> "$final_summary"
            fi
        fi
    done
    
    cat >> "$final_summary" << EOF

## 详细结果文件
- HTML报告: report_\${users}users.html
- CSV数据: results_\${users}users_*.csv
- 详细日志: test_\${users}users.log

## 建议分析点
1. 响应时间随并发数的变化趋势
2. 系统吞吐量的峰值点
3. P95/P99延迟的可接受范围
4. 失败率开始上升的并发数临界点

EOF
    
    log_info "分析报告已生成: $final_summary"
}

# 显示测试进度
show_progress() {
    local current=$1
    local total=$2
    local percent=$((current * 100 / total))
    local bar_length=30
    local filled_length=$((percent * bar_length / 100))
    
    printf "\r进度: ["
    for ((i=0; i<filled_length; i++)); do printf "="; done
    for ((i=filled_length; i<bar_length; i++)); do printf " "; done
    printf "] %d%% (%d/%d)" "$percent" "$current" "$total"
}

# 主函数
main() {
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --host)
                TARGET_HOST="$2"
                shift 2
                ;;
            --run-time)
                RUN_TIME="$2"
                shift 2
                ;;
            --spawn-rate)
                SPAWN_RATE="$2"
                shift 2
                ;;
            --users)
                IFS=',' read -ra USER_COUNTS <<< "$2"
                shift 2
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 显示测试配置
    log_info "=== Locust 批量性能测试 ==="
    log_info "目标主机: $TARGET_HOST"
    log_info "运行时间: $RUN_TIME"
    log_info "用户启动速率: $SPAWN_RATE"
    log_info "测试用户数: ${USER_COUNTS[*]}"
    log_info "结果目录: $TEST_SESSION_DIR"
    echo
    
    # 检查依赖
    check_dependencies
    
    # 测试连通性
    test_connectivity
    
    # 初始化汇总报告
    cat > "$SUMMARY_FILE" << EOF
Locust 批量性能测试汇总报告
生成时间: $(date)
目标主机: $TARGET_HOST
测试配置: 运行时间${RUN_TIME}, 启动速率${SPAWN_RATE}

EOF
    
    # 执行批量测试
    local total_tests=${#USER_COUNTS[@]}
    local current_test=0
    
    log_info "开始执行 $total_tests 个测试..."
    echo
    
    for users in "${USER_COUNTS[@]}"; do
        current_test=$((current_test + 1))
        show_progress "$current_test" "$total_tests"
        echo
        
        if ! run_single_test "$users"; then
            log_error "测试 $users 用户失败，继续下一个测试"
        fi
        
        # 测试间隔，让系统稍作休息
        if [ "$current_test" -lt "$total_tests" ]; then
            log_debug "等待 5 秒后开始下一个测试..."
            sleep 5
        fi
    done
    
    echo
    log_info "所有测试完成!"
    
    # 生成最终分析报告
    generate_final_summary
    
    # 显示结果位置
    log_info "测试结果保存在: $TEST_SESSION_DIR"
    log_info "汇总报告: $SUMMARY_FILE"
    log_info "性能分析: ${TEST_SESSION_DIR}/performance_analysis.txt"
    
    # 显示快速统计
    if command -v bc &> /dev/null; then
        log_info ""
        log_info "=== 快速统计 ==="
        local total_requests=0
        local total_failures=0
        
        for users in "${USER_COUNTS[@]}"; do
            local csv_file="${TEST_SESSION_DIR}/results_${users}users_stats.csv"
            if [ -f "$csv_file" ]; then
                local chat_stats=$(grep "chat_completions" "$csv_file" | tail -1)
                if [ -n "$chat_stats" ]; then
                    IFS=',' read -ra METRICS <<< "$chat_stats"
                    total_requests=$((total_requests + ${METRICS[2]}))
                    total_failures=$((total_failures + ${METRICS[3]}))
                fi
            fi
        done
        
        if [ "$total_requests" -gt 0 ]; then
            local overall_success_rate=$(echo "scale=2; (($total_requests - $total_failures) * 100) / $total_requests" | bc -l)
            log_info "总请求数: $total_requests"
            log_info "总失败数: $total_failures"
            log_info "整体成功率: ${overall_success_rate}%"
        fi
    fi
    
    log_info "批量测试完成! 🎉"
}

# 运行主函数
main "$@"