# Scripts - 工具脚本

This directory contains utility scripts for the Inty backend.

## compress_agent_avatar_image.py

Compresses PNG avatar images to JPEG format and updates the database records.

### Usage

```bash
python scripts/compress_agent_avatar_image.py --pg_url "postgresql://user:password@host:port/database"
```

### Options

- `--pg_url`: PostgreSQL connection URL (required)
- `--quality`: JPEG compression quality 1-100 (default: 80)

### What it does

1. Connects to PostgreSQL database using the provided URL
2. Queries the `agents` table for records with PNG avatar URLs
3. Downloads each PNG image
4. Compresses PNG to JPEG with specified quality
5. Uploads JPEG to Google Cloud Storage in the same directory structure
6. Updates the database record with the new JPEG URL
7. Generates detailed logs of the process

### Requirements

- Valid `config.yaml` with GCS credentials configured
- PostgreSQL database access
- Internet access to download images
- PIL (Pillow) for image processing

### Example

```bash
# Compress with default quality (80)
python scripts/compress_agent_avatar_image.py --pg_url "postgresql://postgres:password@localhost:5432/inty_db"

# Compress with custom quality
python scripts/compress_agent_avatar_image.py --pg_url "postgresql://postgres:password@localhost:5432/inty_db" --quality 90
```

## weekly_ai_industry_report/weekly_ai_industry_report.py

自动生成 AI 行业周报，通过 Google Custom Search 汇总过去 7 天的新闻，再使用 Gemini 模型输出中文摘要，并在成功生成后推送到飞书群机器人。

### 依赖与配置

- `GOOGLE_CSE_API_KEY`：Google Custom Search API 密钥
- `GOOGLE_CSE_ID`：Custom Search Engine ID
- `GEMINI_API_KEY`：Gemini 模型 API Key
- `FEISHU_WEBHOOK_URL`：飞书群机器人 webhook，配置后脚本会自动推送
- `FEISHU_WEBHOOK_SECRET`（可选）：若机器人开启签名校验，则需要设置

### 运行方式

```bash
GOOGLE_CSE_API_KEY=xxx \
GOOGLE_CSE_ID=xxx \
GEMINI_API_KEY=xxx \
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx \
python scripts/weekly_ai_industry_report/weekly_ai_industry_report.py
```

执行成功后会在仓库根目录生成 `ai_weekly_report_<日期>.json`，并在控制台输出飞书推送结果。
