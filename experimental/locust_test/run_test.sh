#！/bin/bash
# Inty Backend Locust 负载测试启动脚本
#作者：Claude
# 日期：2025-08-14

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
# 显示帮助信息
show_help() {
    echo "Inty Backend Locust 负载测试启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help          显示帮助信息"
    echo "  -t, --test-type     测试类型 (basic|stress|peak|stability|custom)"
    echo "  -u, --users         用户数 (默认: 20)"
    echo "  -r, --spawn-rate    用户生成速率 (默认: 2)"
    echo "  -d, --duration      测试持续时间 (默认: 10m)"
    echo "  -H, --host          目标主机 (默认: http://localhost:8000)"
    echo "  --headless          无界面模式"
    echo "  --html              生成HTML报告"
    echo "  --csv               生成CSV数据"
    echo "  --setup             仅启动测试环境"
    echo "  --cleanup           清理测试环境"
    echo "  --monitor           启动监控服务"
    echo ""
    echo "测试类型说明:"
    echo "  basic      基础负载测试 (5-20用户, 10分钟)"
    echo "  stress     压力测试 (20-100用户, 15分钟)"
    echo "  peak       峰值测试 (100-200用户, 5分钟)"
    echo "  stability  稳定性测试 (50用户, 30分钟)"
    echo "  custom     自定义测试 (需要指定参数)"
    echo ""
    echo "示例:"
    echo "  $0 --test-type basic --html"
    echo "  $0 --test-type stress --users 100 --spawn-rate 5 --duration 15m"
    echo "  $0 --setup"
    echo "  $0 --cleanup"
}
#检查依赖关系
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装或不在PATH中"
        exit 1
    fi
#检查Docker Compose （优先使用新的插件语法）
    if docker compose version &> /dev/null; then
        export DOCKER_COMPOSE="docker compose"
        log_info "使用 Docker Compose 插件"
    elif command -v docker-compose &> /dev/null; then
        export DOCKER_COMPOSE="docker-compose"
        log_info "使用独立的 docker-compose"
    else
        log_error "Docker Compose 未安装或不可用"
        log_error "请安装 Docker Compose 或确保 Docker 包含 Compose 插件"
        exit 1
    fi
    
    if [ ! -f "docker-compose.test.yml" ]; then
        log_error "找不到 docker-compose.test.yml 文件"
        exit 1
    fi
    
    if [ ! -f "locustfile.py" ]; then
        log_error "找不到 locustfile.py 文件"
        exit 1
    fi
    
    log_info "依赖检查通过"
}
# 启动测试环境
setup_environment() {
    log_info "启动测试环境..."
#创建必要的目录
    mkdir -p test-data config monitoring/grafana/{dashboards,datasources}
# 拉取生产镜像
    log_info "拉取生产镜像..."
    docker pull ghcr.io/nascentcore/inty-backend/inty-server@sha256:e0bbf5278b78326e9ec096b03f94f64 || {
        log_error "镜像拉取失败，请检查网络连接和权限"
        exit 1
    }
# 启动基础服务
    log_info "启动数据库服务..."
    $DOCKER_COMPOSE -f docker-compose.test.yml up -d postgres
# 等待数据库启动
    log_info "等待数据库启动..."
    sleep 20
# 查看数据库状态
    for i in {1..30}; do
        if $DOCKER_COMPOSE -f docker-compose.test.yml exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
            log_info "数据库已就绪"
            break
        fi
        log_debug "等待数据库启动... ($i/30)"
        sleep 2
    done
# 启动应用服务
    log_info "启动应用服务..."
    $DOCKER_COMPOSE -f docker-compose.test.yml up -d inty-backend
# 等待应用启动
    log_info "等待应用服务启动..."
    sleep 15
# 健康检查
    for i in {1..30}; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            log_info "应用服务已就绪"
            break
        fi
        log_debug "等待应用服务启动... ($i/30)"
        sleep 2
    done
# 验证服务状态
    log_info "验证服务状态..."
    $DOCKER_COMPOSE -f docker-compose.test.yml ps
    
    log_info "测试环境启动完成!"
}
# 启动监控服务
setup_monitoring() {
    log_info "启动监控服务..."
    $DOCKER_COMPOSE -f docker-compose.test.yml --profile monitoring up -d
    
    log_info "监控服务已启动:"
    log_info "  Grafana: http://localhost:3000 (admin/admin123)"
    log_info "  Prometheus: http://localhost:9090"
}
#清理环境
cleanup_environment() {
    log_info "清理测试环境..."
#停止所有服务
    $DOCKER_COMPOSE -f docker-compose.test.yml down -v
#清理Docker资源
    log_info "清理Docker资源..."
    docker system prune -f
    
    log_info "环境清理完成"
}
# 负载负载测试
run_load_test() {
    local test_type=$1
    local users=$2
    local spawn_rate=$3
    local duration=$4
    local host=$5
    local headless=$6
    local html=$7
    local csv=$8
    
    log_info "开始执行负载测试..."
    log_info "  测试类型: $test_type"
    log_info "  用户数: $users"
    log_info "  生成速率: $spawn_rate"
    log_info "  持续时间: $duration"
    log_info "  目标主机: $host"
#生成计时器
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local output_prefix="test-data/${test_type}_${timestamp}"
# 构建命令参数
    local cmd_args="-f locustfile.py --host=$host --users=$users --spawn-rate=$spawn_rate"
    
    if [ "$duration" != "" ]; then
        cmd_args="$cmd_args --run-time=$duration"
    fi
    
    if [ "$headless" = "true" ]; then
        cmd_args="$cmd_args --headless"
    fi
    
    if [ "$html" = "true" ]; then
        cmd_args="$cmd_args --html=${output_prefix}_report.html"
    fi
    
    if [ "$csv" = "true" ]; then
        cmd_args="$cmd_args --csv=${output_prefix}"
    fi
# 启动Locust测试
    if [ "$headless" = "true" ]; then
        log_info "运行无界面测试..."
        locust $cmd_args
    else
        log_info "启动Locust Web界面..."
        $DOCKER_COMPOSE -f docker-compose.test.yml up -d locust-master locust-worker
        log_info "Locust Web界面: http://localhost:8089"
        log_info "请在Web界面中配置测试参数并启动测试"
        log_info "按Ctrl+C停止Locust服务"
# 等待用户中断
        trap '$DOCKER_COMPOSE -f docker-compose.test.yml stop locust-master locust-worker' INT
        while true; do
            sleep 5
        done
    fi
}
# 获取预定义测试配置
get_test_config() {
    local test_type=$1
    
    case $test_type in
        "basic")
            echo "20 2 10m"
            ;;
        "stress")
            echo "100 5 15m"
            ;;
        "peak")
            echo "200 10 5m"
            ;;
        "stability")
            echo "50 5 30m"
            ;;
        *)
            echo ""
            ;;
    esac
}
# 主函数
main() {
# 默认参数
    local test_type="basic"
    local users="20"
    local spawn_rate="2"
    local duration="10m"
    local host="http://localhost:8000"
    local headless="false"
    local html="false"
    local csv="false"
    local setup_only="false"
    local cleanup_only="false"
    local monitor="false"
# 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -t|--test-type)
                test_type="$2"
                shift 2
                ;;
            -u|--users)
                users="$2"
                shift 2
                ;;
            -r|--spawn-rate)
                spawn_rate="$2"
                shift 2
                ;;
            -d|--duration)
                duration="$2"
                shift 2
                ;;
            -H|--host)
                host="$2"
                shift 2
                ;;
            --headless)
                headless="true"
                shift
                ;;
            --html)
                html="true"
                shift
                ;;
            --csv)
                csv="true"
                shift
                ;;
            --setup)
                setup_only="true"
                shift
                ;;
            --cleanup)
                cleanup_only="true"
                shift
                ;;
            --monitor)
                monitor="true"
                shift
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
#检查依赖关系
    check_dependencies
# 处理特殊操作
    if [ "$cleanup_only" = "true" ]; then
        cleanup_environment
        exit 0
    fi
    
    if [ "$setup_only" = "true" ]; then
        setup_environment
        if [ "$monitor" = "true" ]; then
            setup_monitoring
        fi
        exit 0
    fi
# 获取预配置定义
    if [ "$test_type" != "custom" ]; then
        local config=$(get_test_config "$test_type")
        if [ "$config" != "" ]; then
            read -r users spawn_rate duration <<< "$config"
        fi
    fi
# 启动环境
    setup_environment
    
    if [ "$monitor" = "true" ]; then
        setup_monitoring
    fi
# 执行测试
    run_load_test "$test_type" "$users" "$spawn_rate" "$duration" "$host" "$headless" "$html" "$csv"
}
# 运行主函数
main "$@"