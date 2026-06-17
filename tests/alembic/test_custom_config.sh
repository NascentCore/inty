#!/usr/bin/env bash
# 验证 Alembic env.py 会使用 -x config=... 指定的配置连接数据库

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BASE_CONFIG_PATH="${REPO_ROOT}/devops/config.yaml.local"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

# 获取 PostgreSQL 连接参数
get_postgres_params() {
    PG_USER="${PG_USER:-postgres}"
    PG_PASSWORD="${PG_PASSWORD:-sxwl666!}"
    PG_HOST="${PG_HOST:-localhost}"
    PG_PORT="${PG_PORT:-5432}"
}

# 尝试连接管理数据库
get_admin_dbname() {
    local candidates=("${PG_MAINTENANCE_DB:-}" "postgres" "${PG_DB:-}" "inty")
    for dbname in "${candidates[@]}"; do
        [ -z "$dbname" ] && continue
        if PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$dbname" -c "SELECT 1" >/dev/null 2>&1; then
            echo "$dbname"
            return 0
        fi
    done
    log_error "无法连接 Postgres 管理库"
    return 1
}

# 重建数据库
recreate_database() {
    local dbname="$1"
    local admin_db
    admin_db="$(get_admin_dbname)"
    
    log_info "重建数据库: $dbname"
    PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$admin_db" <<EOF
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '$dbname';

DROP DATABASE IF EXISTS "$dbname";
CREATE DATABASE "$dbname";
EOF
}

# 删除数据库
drop_database() {
    local dbname="$1"
    local admin_db
    admin_db="$(get_admin_dbname)"
    
    log_info "删除数据库: $dbname"
    PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$admin_db" <<EOF
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '$dbname';

DROP DATABASE IF EXISTS "$dbname";
EOF
}

# 生成自定义配置文件
write_custom_config() {
    local config_path="$1"
    local dbname="$2"
    
    if [ ! -f "$BASE_CONFIG_PATH" ]; then
        log_error "$BASE_CONFIG_PATH 不存在，无法生成 Alembic 测试配置"
        return 1
    fi
    
    log_info "生成自定义配置文件: $config_path"
    
    cp "$BASE_CONFIG_PATH" "$config_path"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/db: \"inty\"/db: $dbname/" "$config_path"
    else
        sed -i "s/db: \"inty\"/db: $dbname/" "$config_path"
    fi
    cat "$config_path"
}

# 获取 Alembic 版本
fetch_alembic_version() {
    local dbname="$1"
    PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$dbname" -t -c "SELECT version_num FROM alembic_version LIMIT 1" | tr -d '[:space:]'
}

# 主测试函数
main() {
    log_info "开始测试 Alembic 自定义配置功能"
    
    get_postgres_params
    
    # 生成唯一数据库名
    db_name="alembic_test_$(openssl rand -hex 4)"
    config_path="$(mktemp -t alembic_test_config_XXXXXX.yaml)"
    
    # 清理函数
    cleanup() {
        log_info "清理测试环境"
        [ -f "$config_path" ] && rm -f "$config_path"
        drop_database "$db_name" 2>/dev/null || true
    }
    trap cleanup EXIT
    
    log_info "测试数据库: $db_name"
    log_info "配置文件: $config_path"
    
    # 重建数据库
    recreate_database "$db_name"
    
    # 生成自定义配置
    write_custom_config "$config_path" "$db_name"
    
    # app.core.config 在模型导入链上会被加载；用 INTY_CONFIG_YAML 指向本次 Alembic 自定义配置
    export INTY_CONFIG_YAML="$config_path"

    if ! python -m alembic -c "${REPO_ROOT}/backend/alembic/alembic.ini" -x "config=$config_path" upgrade head; then
        log_error "Alembic upgrade 失败"
        return 1
    fi
    
    # 检查版本
    version="$(fetch_alembic_version "$db_name")"
    if [ -z "$version" ]; then
        log_error "Alembic 未在自定义数据库内记录版本"
        return 1
    fi
    
    log_info "✓ 测试通过: Alembic 版本 $version 已记录在数据库 $db_name"
    return 0
}

# 运行测试
if ! main; then
    log_error "测试失败"
    exit 1
fi

log_info "所有测试通过"
exit 0

