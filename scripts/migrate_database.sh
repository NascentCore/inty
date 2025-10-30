#!/bin/bash

################################################################################
# 数据库迁移脚本：SOURCE → SINK
# 
# 用途：自动化执行从源数据库到目标数据库的完整数据迁移
# 
# 使用方法：
#   ./migrate_database.sh [选项]
#
# 选项：
#   --source-host HOST      源数据库主机
#   --source-port PORT      源数据库端口（默认 5432）
#   --source-db DATABASE    源数据库名称
#   --source-user USER      源数据库用户
#   --sink-host HOST        目标数据库主机
#   --sink-port PORT        目标数据库端口（默认 5432）
#   --sink-db DATABASE      目标数据库名称
#   --sink-user USER        目标数据库用户
#   --backup-dir PATH       备份目录（默认 /tmp/db_migration_TIMESTAMP）
#   --parallel-jobs N       并行任务数（默认 4）
#   --skip-verify          跳过数据验证
#   --skip-optimize        跳过优化步骤
#   --dry-run              只检查不执行
#   -h, --help             显示帮助信息
#
# 示例：
#   ./migrate_database.sh \
#       --source-host db1.example.com --source-db proddb --source-user postgres \
#       --sink-host db2.example.com --sink-db proddb --sink-user postgres
#
################################################################################

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认值
SOURCE_HOST=""
SOURCE_PORT="5432"
SOURCE_DB=""
SOURCE_USER="postgres"
SINK_HOST=""
SINK_PORT="5432"
SINK_DB=""
SINK_USER="postgres"
BACKUP_DIR="/tmp/db_migration_$(date +%Y%m%d_%H%M%S)"
PARALLEL_JOBS=4
SKIP_VERIFY=false
SKIP_OPTIMIZE=false
DRY_RUN=false

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    head -n 40 "$0" | grep "^#" | sed 's/^# \?//'
    exit 0
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --source-host)
                SOURCE_HOST="$2"
                shift 2
                ;;
            --source-port)
                SOURCE_PORT="$2"
                shift 2
                ;;
            --source-db)
                SOURCE_DB="$2"
                shift 2
                ;;
            --source-user)
                SOURCE_USER="$2"
                shift 2
                ;;
            --sink-host)
                SINK_HOST="$2"
                shift 2
                ;;
            --sink-port)
                SINK_PORT="$2"
                shift 2
                ;;
            --sink-db)
                SINK_DB="$2"
                shift 2
                ;;
            --sink-user)
                SINK_USER="$2"
                shift 2
                ;;
            --backup-dir)
                BACKUP_DIR="$2"
                shift 2
                ;;
            --parallel-jobs)
                PARALLEL_JOBS="$2"
                shift 2
                ;;
            --skip-verify)
                SKIP_VERIFY=true
                shift
                ;;
            --skip-optimize)
                SKIP_OPTIMIZE=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                show_help
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                ;;
        esac
    done

    # 验证必需参数
    if [[ -z "$SOURCE_HOST" || -z "$SOURCE_DB" || -z "$SINK_HOST" || -z "$SINK_DB" ]]; then
        log_error "缺少必需参数"
        show_help
    fi
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖工具..."
    
    local missing_deps=()
    
    for cmd in pg_dump pg_restore psql; do
        if ! command -v $cmd &> /dev/null; then
            missing_deps+=($cmd)
        fi
    done
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_error "缺少以下依赖: ${missing_deps[*]}"
        log_error "请安装 PostgreSQL 客户端工具"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# 测试数据库连接
test_connection() {
    local host=$1
    local port=$2
    local db=$3
    local user=$4
    local label=$5
    
    log_info "测试 $label 数据库连接: $user@$host:$port/$db"
    
    if $DRY_RUN; then
        log_info "[DRY RUN] 跳过连接测试"
        return 0
    fi
    
    if psql -h "$host" -p "$port" -U "$user" -d "$db" -c "SELECT 1" &> /dev/null; then
        log_success "$label 连接成功"
        return 0
    else
        log_error "$label 连接失败"
        return 1
    fi
}

# 获取数据库大小
get_db_size() {
    local host=$1
    local port=$2
    local db=$3
    local user=$4
    
    psql -h "$host" -p "$port" -U "$user" -d "$db" -t -c "
        SELECT pg_size_pretty(pg_database_size('$db'));
    " | xargs
}

# 获取表行数
get_table_count() {
    local host=$1
    local port=$2
    local db=$3
    local user=$4
    
    psql -h "$host" -p "$port" -U "$user" -d "$db" -t -c "
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    " | xargs
}

# 检查 SINK 是否为空
check_sink_empty() {
    log_info "检查目标数据库是否为空..."
    
    if $DRY_RUN; then
        log_info "[DRY RUN] 跳过空库检查"
        return 0
    fi
    
    local total_rows=$(psql -h "$SINK_HOST" -p "$SINK_PORT" -U "$SINK_USER" -d "$SINK_DB" -t -A -c "
        SELECT SUM(n_live_tup) 
        FROM pg_stat_user_tables;
    " | xargs)
    
    if [[ -z "$total_rows" || "$total_rows" == "0" ]]; then
        log_success "目标数据库为空，可以继续"
        return 0
    else
        log_warning "目标数据库包含 $total_rows 行数据"
        read -p "是否继续？这将清空目标数据库 [y/N]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "用户取消操作"
            exit 1
        fi
        
        # 清空目标数据库
        log_info "清空目标数据库..."
        psql -h "$SINK_HOST" -p "$SINK_PORT" -U "$SINK_USER" -d "$SINK_DB" << 'EOF'
DO $$ 
DECLARE 
    r RECORD;
BEGIN
    -- 禁用触发器
    SET session_replication_role = 'replica';
    
    -- 删除所有数据
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
    
    -- 恢复触发器
    SET session_replication_role = 'origin';
END $$;
EOF
        log_success "目标数据库已清空"
    fi
}

# 创建备份目录
create_backup_dir() {
    log_info "创建备份目录: $BACKUP_DIR"
    
    if $DRY_RUN; then
        log_info "[DRY RUN] 跳过目录创建"
        return 0
    fi
    
    mkdir -p "$BACKUP_DIR"
    log_success "备份目录已创建"
}

# 导出数据
export_data() {
    log_info "从 SOURCE 导出数据..."
    log_info "数据库大小: $(get_db_size "$SOURCE_HOST" "$SOURCE_PORT" "$SOURCE_DB" "$SOURCE_USER")"
    log_info "表数量: $(get_table_count "$SOURCE_HOST" "$SOURCE_PORT" "$SOURCE_DB" "$SOURCE_USER")"
    
    if $DRY_RUN; then
        log_info "[DRY RUN] 跳过数据导出"
        return 0
    fi
    
    local dump_file="${BACKUP_DIR}/data_only.dump"
    
    log_info "导出到文件: $dump_file"
    log_info "这可能需要几分钟到几小时，请耐心等待..."
    
    if pg_dump -h "$SOURCE_HOST" -p "$SOURCE_PORT" -U "$SOURCE_USER" \
        --format=custom \
        --data-only \
        --verbose \
        --file="$dump_file" \
        "$SOURCE_DB" 2>&1 | tee "${BACKUP_DIR}/export.log"; then
        log_success "数据导出完成"
        
        # 显示文件大小
        local file_size=$(du -h "$dump_file" | cut -f1)
        log_info "导出文件大小: $file_size"
    else
        log_error "数据导出失败，请查看日志: ${BACKUP_DIR}/export.log"
        exit 1
    fi
}

# 导出序列
export_sequences() {
    log_info "导出序列当前值..."
    
    if $DRY_RUN; then
        log_info "[DRY RUN] 跳过序列导出"
        return 0
    fi
    
    local seq_file="${BACKUP_DIR}/sequences_reset.sql"
    
    psql -h "$SOURCE_HOST" -p "$SOURCE_PORT" -U "$SOURCE_USER" -d "$SOURCE_DB" -t -A << 'EOF' > "$seq_file"
SELECT 'SELECT setval(' || quote_literal(sequence_schema || '.' || sequence_name) || ', ' || 
       'COALESCE((SELECT MAX(' || column_name || ') FROM ' || table_schema || '.' || table_name || '), 1), true);'
FROM information_schema.sequences seq
LEFT JOIN information_schema.columns col 
    ON col.column_default LIKE '%' || seq.sequence_name || '%'
WHERE sequence_schema = 'public'
ORDER BY sequence_name;
EOF
    
    log_success "序列导出完成: $seq_file"
}

# 导入数据
import_data() {
    log_info "导入数据到 SINK..."
    log_info "使用 $PARALLEL_JOBS 个并行任务"
    
    if $DRY_RUN; then
        log_info "[DRY RUN] 跳过数据导入"
        return 0
    fi
    
    local dump_file="${BACKUP_DIR}/data_only.dump"
    
    # 禁用触发器
    log_info "禁用触发器..."
    psql -h "$SINK_HOST" -p "$SINK_PORT" -U "$SINK_USER" -d "$SINK_DB" << 'EOF'
SET session_replication_role = 'replica';
EOF
    
    # 导入数据
    log_info "开始导入数据..."
    if pg_restore -h "$SINK_HOST" -p "$SINK_PORT" -U "$SINK_USER" \
        --dbname="$SINK_DB" \
        --jobs="$PARALLEL_JOBS" \
        --verbose \
        --data-only \
        --disable-triggers \
        "$dump_file" 2>&1 | tee "${BACKUP_DIR}/import.log"; then
        log_success "数据导入完成"
    else
        log_warning "数据导入完成但有警告，请查看日志: ${BACKUP_DIR}/import.log"
    fi
    
    # 启用触发器
    log_info "启用触发器..."
    psql -h "$SINK_HOST" -p "$SINK_PORT" -U "$SINK_USER" -d "$SINK_DB" << 'EOF'
SET session_replication_role = 'origin';
EOF
}

# 重置序列
reset_sequences() {
    log_info "重置序列值..."
    
    if $DRY_RUN; then
        log_info "[DRY RUN] 跳过序列重置"
        return 0
    fi
    
    local seq_file="${BACKUP_DIR}/sequences_reset.sql"
    
    if [ -f "$seq_file" ]; then
        psql -h "$SINK_HOST" -p "$SINK_PORT" -U "$SINK_USER" -d "$SINK_DB" \
            -f "$seq_file" &> "${BACKUP_DIR}/sequences.log"
        log_success "序列重置完成"
    else
        log_warning "序列文件不存在，跳过"
    fi
}

# 验证数据
verify_data() {
    if $SKIP_VERIFY; then
        log_info "跳过数据验证"
        return 0
    fi
    
    log_info "验证数据完整性..."
    
    if $DRY_RUN; then
        log_info "[DRY RUN] 跳过数据验证"
        return 0
    fi
    
    local comparison_file="${BACKUP_DIR}/row_count_comparison.txt"
    
    # 比对行数
    log_info "比对表行数..."
    
    cat > "${BACKUP_DIR}/count_rows.sql" << 'EOF'
SELECT 
    schemaname, 
    tablename,
    n_live_tup as row_count
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY tablename;
EOF
    
    echo "=== SOURCE 数据库行数 ===" > "$comparison_file"
    psql -h "$SOURCE_HOST" -p "$SOURCE_PORT" -U "$SOURCE_USER" -d "$SOURCE_DB" \
        -f "${BACKUP_DIR}/count_rows.sql" >> "$comparison_file"
    
    echo -e "\n=== SINK 数据库行数 ===" >> "$comparison_file"
    psql -h "$SINK_HOST" -p "$SINK_PORT" -U "$SINK_USER" -d "$SINK_DB" \
        -f "${BACKUP_DIR}/count_rows.sql" >> "$comparison_file"
    
    log_info "行数比对结果已保存到: $comparison_file"
    
    # 简单比对
    local source_total=$(psql -h "$SOURCE_HOST" -p "$SOURCE_PORT" -U "$SOURCE_USER" -d "$SOURCE_DB" -t -c "
        SELECT SUM(n_live_tup) FROM pg_stat_user_tables WHERE schemaname = 'public';
    " | xargs)
    
    local sink_total=$(psql -h "$SINK_HOST" -p "$SINK_PORT" -U "$SINK_USER" -d "$SINK_DB" -t -c "
        SELECT SUM(n_live_tup) FROM pg_stat_user_tables WHERE schemaname = 'public';
    " | xargs)
    
    log_info "SOURCE 总行数: $source_total"
    log_info "SINK 总行数: $sink_total"
    
    if [[ "$source_total" == "$sink_total" ]]; then
        log_success "✅ 总行数匹配"
    else
        log_warning "⚠️  总行数不匹配，请检查详细报告: $comparison_file"
    fi
}

# 优化数据库
optimize_database() {
    if $SKIP_OPTIMIZE; then
        log_info "跳过数据库优化"
        return 0
    fi
    
    log_info "优化目标数据库..."
    
    if $DRY_RUN; then
        log_info "[DRY RUN] 跳过数据库优化"
        return 0
    fi
    
    # 更新统计信息
    log_info "更新统计信息..."
    psql -h "$SINK_HOST" -p "$SINK_PORT" -U "$SINK_USER" -d "$SINK_DB" -c "ANALYZE VERBOSE;" \
        &> "${BACKUP_DIR}/analyze.log"
    log_success "统计信息更新完成"
    
    # VACUUM
    log_info "执行 VACUUM..."
    psql -h "$SINK_HOST" -p "$SINK_PORT" -U "$SINK_USER" -d "$SINK_DB" -c "VACUUM ANALYZE;" \
        &> "${BACKUP_DIR}/vacuum.log"
    log_success "VACUUM 完成"
}

# 生成迁移报告
generate_report() {
    log_info "生成迁移报告..."
    
    local report_file="${BACKUP_DIR}/migration_report.txt"
    
    cat > "$report_file" << EOF
================================================================================
数据库迁移报告
================================================================================

迁移时间: $(date)

源数据库:
  主机: $SOURCE_HOST:$SOURCE_PORT
  数据库: $SOURCE_DB
  用户: $SOURCE_USER

目标数据库:
  主机: $SINK_HOST:$SINK_PORT
  数据库: $SINK_DB
  用户: $SINK_USER

配置:
  并行任务数: $PARALLEL_JOBS
  备份目录: $BACKUP_DIR
  跳过验证: $SKIP_VERIFY
  跳过优化: $SKIP_OPTIMIZE

文件列表:
$(ls -lh "$BACKUP_DIR")

日志文件:
  - export.log: 数据导出日志
  - import.log: 数据导入日志
  - sequences.log: 序列重置日志
  - analyze.log: 统计分析日志
  - vacuum.log: VACUUM 日志
  - row_count_comparison.txt: 行数比对报告

================================================================================
EOF
    
    cat "$report_file"
    log_success "迁移报告已保存到: $report_file"
}

# 主函数
main() {
    echo "=========================================="
    echo "   数据库迁移工具 v1.0"
    echo "=========================================="
    echo
    
    # 解析参数
    parse_args "$@"
    
    # 检查依赖
    check_dependencies
    
    # 测试连接
    test_connection "$SOURCE_HOST" "$SOURCE_PORT" "$SOURCE_DB" "$SOURCE_USER" "SOURCE"
    test_connection "$SINK_HOST" "$SINK_PORT" "$SINK_DB" "$SINK_USER" "SINK"
    
    # 显示信息
    log_info "源数据库: $SOURCE_USER@$SOURCE_HOST:$SOURCE_PORT/$SOURCE_DB"
    log_info "目标数据库: $SINK_USER@$SINK_HOST:$SINK_PORT/$SINK_DB"
    log_info "备份目录: $BACKUP_DIR"
    
    if $DRY_RUN; then
        log_warning "这是一次 DRY RUN，不会执行实际操作"
    fi
    
    # 确认继续
    if ! $DRY_RUN; then
        echo
        log_warning "即将开始迁移，请确认以上信息无误"
        read -p "是否继续？[y/N]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "用户取消操作"
            exit 1
        fi
    fi
    
    # 开始迁移
    START_TIME=$(date +%s)
    
    create_backup_dir
    check_sink_empty
    export_data
    export_sequences
    import_data
    reset_sequences
    verify_data
    optimize_database
    generate_report
    
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo
    echo "=========================================="
    log_success "🎉 迁移完成！"
    log_info "总耗时: $((DURATION / 60)) 分 $((DURATION % 60)) 秒"
    log_info "备份目录: $BACKUP_DIR"
    echo "=========================================="
    echo
    log_info "下一步："
    log_info "1. 查看迁移报告: cat ${BACKUP_DIR}/migration_report.txt"
    log_info "2. 查看行数比对: cat ${BACKUP_DIR}/row_count_comparison.txt"
    log_info "3. 测试应用连接到 SINK 数据库"
    log_info "4. 如无问题，更新生产配置指向 SINK"
    log_info "5. 保留 SOURCE 作为备份至少 7 天"
    echo
}

# 错误处理
trap 'log_error "脚本执行失败，退出码: $?"' ERR

# 执行主函数
main "$@"
