# Scripts - 工具脚本

This directory contains utility scripts for the Inty backend.

- **delete_festival_memories_and_prompts.py**：删除所有节日记忆（memory 表 `memory_type=festival`）及对应的「节日记忆提示」类 chat_history。默认 dry-run；实际执行请使用 `--no-dry-run`，可选 `--yes` 跳过交互确认。
- **create_mock_user_agent_memory.py**：为指定 (user_id, agent_id) 创建一条 mock 记忆及对应消息（节日记忆提示 + 可选 mock 人机对话）。必填 `user_id`、`agent_id`；可选 `--memory-type`（festival/user_agent）、`--festival-config-id` 或 `--festival-name`/`--festival-date`、`--content`、`--add-mock-chat`；默认 dry-run，实际执行用 `--no-dry-run`，可选 `--yes`。
- **export_festival_memory_replica.py**：从 inty 生产只读副本查询指定节日记忆（默认 Christmas 2026），导出为 JSON。默认读取 `devops/config.yaml.prod` 的 replica 配置；可覆盖 `--config`、`--output`。需在能访问副本网络的环境运行（如与数据库同 VPC 或 VPN）。密码等敏感信息勿提交，用环境变量 `DB_PASSWORD`、`DB_REPLICA_HOST` 等覆盖。
- **query_chat_history_by_date.py**：按日期与可选条件查询 chat_history，输出匹配的 (user_id, agent_id) 对及可选消息列表；默认从只读副本读取，复用节日记忆的 28 小时时间窗与轮数筛选逻辑。见下方「Query chat history by date」。

## Query chat history by date

按日期（及可选 timezone、min_rounds、user_id、agent_id）从 chat_history 查找匹配的会话对，并可选择拉取完整消息列表。**默认从只读副本**（config 中 `replica_host`/`replica_port`）读取；未配置副本时须加 `--no-replica` 改为主库。逻辑复用 `app.services.festival_memory_service`（28 小时时间窗、用户消息数阈值、按会话拉消息）。

### 参数

- `--date`：日期 YYYY-MM-DD（必填），用于 28 小时时间窗（该时区当日 00:00 至次日 04:00）。
- `--timezone`：时间窗所在时区（默认 `UTC`）。
- `--min-rounds`：时间窗内用户消息数（不含开场白）至少达到此数才纳入（默认 15）。
- `--user-id` / `--agent-id`：可选，将结果限制为指定用户或单会话。
- `--output-json`：可选，将结果写入该 JSON 文件。
- `--include-messages`：为每个匹配对拉取完整消息列表并写入输出。
- `--replica` / `--no-replica`：是否从只读副本读取（默认 `--replica`）。副本需在 config 中配置 `replica_host`。
- `--config`：可选，复制此 YAML 到当前目录 `config.yaml` 后再导入 app；不指定则要求当前目录下已存在 `config.yaml`（通常在仓库根目录运行）。

### 示例

```bash
export PYTHONPATH=.
python scripts/query_chat_history_by_date.py --date 2025-12-25
python scripts/query_chat_history_by_date.py --date 2025-12-25 --timezone America/Los_Angeles --output-json out.json --include-messages
python scripts/query_chat_history_by_date.py --config devops/config.yaml.prod --date 2025-12-25 --min-rounds 10
python scripts/query_chat_history_by_date.py --no-replica --date 2025-12-25
```

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
