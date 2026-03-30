# INTY v2 本地文本聊天原型

首先，在命令行安装 `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
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

## Memory 语义存储（内存主读 + PostgreSQL 异步持久化 + 文件镜像）

原型中的 Memory 文档（如 `IDENTITY.md`、`SOUL.md`、`USER.md`、`MEMORY.md` 与 `memory/*.md`）已切换为：

1. **MemoryCache（内存主读）**：写后立即可读，下一轮 prompt 直接可见；
2. **PostgresMemoryRepository（可选）**：后台异步 flush 到 PostgreSQL；
3. **MemoryFileMirror（默认开启）**：继续写回本地 `.md` 文件，便于本地调试与人工检查。

`transcript.jsonl`、`llm_trace.jsonl`、`tool_background.jsonl` 继续走原文件链路，不在本轮迁移范围内。

### PostgreSQL 配置

当设置了 `INTY_V2_PROTO_MEMORY_PG_DSN` 时，程序会启用 PostgreSQL 持久化并自动建表：

- 表名默认：`proto_memory_docs`
- 可通过 `INTY_V2_PROTO_MEMORY_PG_TABLE` 覆盖

示例：

```bash
export INTY_V2_PROTO_MEMORY_PG_DSN='postgresql://postgres:sxwl666!@127.0.0.1:5432/inty'
export INTY_V2_PROTO_MEMORY_PG_TABLE='proto_memory_docs'
```

### 关键环境变量

- `INTY_V2_PROTO_MEMORY_PG_DSN`：PostgreSQL DSN；未设置则仅内存 + 文件镜像
- `INTY_V2_PROTO_MEMORY_PG_TABLE`：PG 表名（默认 `proto_memory_docs`）
- `INTY_V2_PROTO_MEMORY_FLUSH_BATCH_SIZE`：异步 flush 批大小（默认 `64`）
- `INTY_V2_PROTO_MEMORY_MIRROR_TO_FILES`：是否开启文件镜像（默认开启，`1/true/yes/on`）

### 关闭/退出行为

CLI 命令（`init-workspace` / `bootstrap-agent` / `repl` / `once`）退出前会执行：

- `flush_now`：等待已入队 Memory 写入完成
- `shutdown`：停止 Memory flush worker 线程
