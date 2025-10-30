#!/bin/bash

# 复制数据库数据，从数据库 A 到数据库 B
# 数据库 A B 具有完全相同的表结构

SOURCE_DB="$1" # postgresql://user:pass@host:port/db
DEST_DB="$2"   # postgresql://user:pass@host:port/db

# 提取数据库连接参数
extract_host() {
    echo "$1" | cut -d'/' -f3 | cut -d':' -f1
}

extract_port() {
    echo "$1" | cut -d'/' -f3 | cut -d':' -f2
}

extract_user() {
    echo "$1" | cut -d'/' -f4
}

extract_db() {
    echo "$1" | cut -d'/' -f5
}

# 检查源数据库是否存在
SOURCE_HOST=$(extract_host "$SOURCE_DB")
SOURCE_PORT=$(extract_port "$SOURCE_DB")
if ! pg_isready -h "$SOURCE_HOST" -p "$SOURCE_PORT"; then
    echo "源数据库不存在"
    exit 1
fi

# 检查目标数据库是否存在
DEST_HOST=$(extract_host "$DEST_DB")
DEST_PORT=$(extract_port "$DEST_DB")
if ! pg_isready -h "$DEST_HOST" -p "$DEST_PORT"; then
    echo "目标数据库不存在"
    exit 1
fi

# 复制数据
SOURCE_USER=$(extract_user "$SOURCE_DB")
SOURCE_DBNAME=$(extract_db "$SOURCE_DB")
DEST_USER=$(extract_user "$DEST_DB")
DEST_DBNAME=$(extract_db "$DEST_DB")

pg_dump \
    -h "$SOURCE_HOST" \
    -p "$SOURCE_PORT" \
    -U "$SOURCE_USER" \
    -d "$SOURCE_DBNAME" \
    | psql \
    -h "$DEST_HOST" \
    -p "$DEST_PORT" \
    -U "$DEST_USER" \
    -d "$DEST_DBNAME"

echo "数据库复制操作完成"
