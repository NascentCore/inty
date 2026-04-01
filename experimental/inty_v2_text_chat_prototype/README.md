# INTY v2 本地文本聊天原型

首先，在命令行安装 `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

拷贝默认配置文件到代码仓库的顶层目录（在代码库顶层目录运行）：

```bash
cp devops/config.yaml.dev config.yaml
```

然后启动本地的聊天服务的界面：

```bash
cd experimental/inty_v2_text_chat_prototype
cp .env.example .env

# 编辑 .env 将自己的名字替补掉 LANGSMITH_PROJECT=inty-v2-text-chat-prototype-<USER>
# 如：LANGSMITH_PROJECT=inty-v2-text-chat-prototype-yaxiongzhao
# 这样方便区分 langsmith 内容

uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python main.py repl --workspace _ws
```

## Memory 语义存储（DB-first 历史版本 + 内存主读 + 文件镜像）

原型中的 Memory 文档（如 `IDENTITY.md`、`SOUL.md`、`USER.md`、`MEMORY.md` 与 `memory/*.md`）已切换为：

1. **PostgresMemoryRepository（可选）**：**先写数据库**，每次更新追加一条历史记录（append-only）；
2. **MemoryCache（内存主读）**：仅在 DB 写成功后更新，保证与 DB 提交状态一致；
3. **MemoryFileMirror（默认开启）**：仅在 DB 写成功后镜像到本地 `.md` 文件，便于本地调试与人工检查。

> 最新版本判定只使用 `sequence_id`（数据库自增主键）；`version` 字段已移除。

## JSONL 事件流（DB-first + 文件镜像）

以下三条 JSONL 事件流也支持 DB-first 写入：

- `transcript.jsonl`
- `llm_trace.jsonl`
- `tool_background.jsonl`

写入顺序为：先写 PostgreSQL（JSONB payload），成功后再 append 本地 `.jsonl` 文件。

### PostgreSQL 配置

当设置了 `INTY_V2_PROTO_MEMORY_PG_DSN` 时，程序会启用 PostgreSQL 持久化并自动建表：

- 表名默认：`proto_memory_doc_versions`
- 可通过 `INTY_V2_PROTO_MEMORY_PG_TABLE` 覆盖

示例：

```bash
export INTY_V2_PROTO_MEMORY_PG_DSN='postgresql://postgres:sxwl666!@127.0.0.1:5432/inty'
export INTY_V2_PROTO_MEMORY_PG_TABLE='proto_memory_doc_versions'
export INTY_V2_PROTO_JSONL_PG_DSN='postgresql://postgres:sxwl666!@127.0.0.1:5432/inty'
export INTY_V2_PROTO_JSONL_PG_TABLE='proto_workspace_jsonl_events'
```

### 关键环境变量

- `INTY_V2_PROTO_MEMORY_PG_DSN`：PostgreSQL DSN；未设置则仅内存 + 文件镜像
- `INTY_V2_PROTO_MEMORY_PG_TABLE`：Memory 历史表名（默认 `proto_memory_doc_versions`）
- `INTY_V2_PROTO_MEMORY_MIRROR_TO_FILES`：是否开启文件镜像（默认开启，`1/true/yes/on`）
- `INTY_V2_PROTO_JSONL_PG_DSN`：JSONL 事件入库 DSN（未设置时回退到 `INTY_V2_PROTO_MEMORY_PG_DSN`）
- `INTY_V2_PROTO_JSONL_PG_TABLE`：JSONL 事件表名（默认 `proto_workspace_jsonl_events`）

### 关闭/退出行为

CLI 命令（`init-workspace` / `bootstrap-agent` / `repl` / `once`）退出前会执行：

- 先 `flush`（Memory + JSONL）
- 再 `shutdown`（Memory + JSONL）

两者都保证幂等，可重复调用。
