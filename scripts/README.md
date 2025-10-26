# 脚本

该目录包含 Inty 后端的实用程序脚本。

## compress_agent_avatar_image.py

Compr将PNG头像图像转换为JPEG格式并更新数据库记录。＃＃＃ 用法```bash
python scripts/compress_agent_avatar_image.py --pg_url "postgresql://user:password@host:port/database"
```＃＃＃ 选项

-`--pg_url`：PostgreSQL连接URL（必填）
-`--quality`：JPEG compr会话质量 1-100（默认值：80）

### 它的作用

1. 使用 provided URL 连接到 PostgreSQL 数据库
2.查询`agents`包含 PNG 头像 URL 的记录表
3.下载每个PNG图像
4. Compr以指定质量将 PNG 转为 JPEG
5.将JPEG上传到Google Cloud Storage相同的目录结构中
6. 使用新的 JPEG URL 更新数据库记录
7.生成 process 的详细日志

＃＃＃ 要求

- 有效的`config.yaml`配置了 GCS 凭据
- PostgreSQL数据库访问
- 访问互联网下载图像
- 图像 processing 的 PIL（枕头）

＃＃＃ 例子```bash
# Compress with default quality (80)
python scripts/compress_agent_avatar_image.py --pg_url "postgresql://postgres:password@localhost:5432/inty_db"

# Compress with custom quality
python scripts/compress_agent_avatar_image.py --pg_url "postgresql://postgres:password@localhost:5432/inty_db" --quality 90
```
