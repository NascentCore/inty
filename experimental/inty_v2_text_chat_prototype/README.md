# INTY v2 本地文本聊天原型

依据仓库文档 `docs/INTY_v2_CORE_AGENTIC_COMPONENT_TECH_PROTOTYPE.md`：单进程 CLI、Markdown + JSONL 文件持久化、**无 HTTP、无数据库**。与 `docs/INTY_v2_CORE_AGENTIC_COMPONENT_TECH_ARCHITECTURE.md` **§3（编排）**、**§20（单一写入路径）** 对齐：助手对用户可见文本仅通过 `orchestrator.run_turn` 追加到 `transcript.jsonl`。

## 依赖

本目录 [requirements.txt](requirements.txt)（`cyclopts`、`openai`、`pydantic`、`python-dotenv`、`loguru`）。建议在 `inty` 仓库根虚拟环境中安装：

```bash
cd /path/to/inty
uv pip install -r experimental/inty_v2_text_chat_prototype/requirements.txt
```

REPL 的 **`generate_image`**（Fal **z-image-turbo** 文生图）复用 [`app/core/images/fal.py`](../../app/core/images/fal.py)；模型按对话在工具参数中填写 `num_images`（默认 1，单次上限 4）。需在同一 venv 中安装**仓库根** [`requirements.txt`](../../requirements.txt)（含 `fal-client`、GCS 等），并具备：

- `FAL_KEY`（与 [fal 文档](https://fal.ai/docs) 一致；与后端一致）
- 仓库根可用的 `config.yaml`（含 `gcs.bucket` 等，与后端测试环境相同；可从 `devops/config.yaml.test` 复制为 `config.yaml` 再按需改）
- 可选：`INTY_V2_PROTO_Z_IMAGE_GCS_BASE` — GCS 对象路径前缀；省略则为 `inty_v2_proto_chat_images/<workspace 目录名>`

**环境变量放哪里：** 建议在 **`inty` 仓库根** 的 `.env`（与 `config.yaml` 同级）中设置 `FAL_KEY` 以及 `OPENROUTER_API_KEY` / `OPENAI_API_KEY`。入口与 `generate_image` 会先加载该路径再加载当前工作目录下的 `.env`，因此在 `experimental/inty_v2_text_chat_prototype/` 里直接运行 `python main.py` 也能读到仓库根的 `.env`。勿将 `.env` 提交到 git（仓库已忽略）。

无上述 Fal/GCS 条件时，模型仍可对话，但调用 `generate_image` 会返回以 `ERROR:` 开头的工具结果。

## 运行方式

在 **`inty/` 目录下**执行（保证 `experimental` 包可解析）：

```bash
cd /path/to/inty
export OPENROUTER_API_KEY=...   # 或 OPENAI_API_KEY（直连 OpenAI）
export INTY_V2_PROTO_MODEL=openai/gpt-4o-mini   # 可选；记忆精炼可用 INTY_V2_PROTO_MEMORY_MODEL
# 可选：SOUL.md 策展（默认与 MEMORY 同模型）；关闭自动写 SOUL：INTY_V2_PROTO_SOUL_UPDATE_DISABLED=1

python -m experimental.inty_v2_text_chat_prototype.main init-workspace --path ./experimental/inty_v2_text_chat_prototype/_ws
python -m experimental.inty_v2_text_chat_prototype.main repl --workspace ./experimental/inty_v2_text_chat_prototype/_ws
python -m experimental.inty_v2_text_chat_prototype.main once --message "你好" --workspace ./experimental/inty_v2_text_chat_prototype/_ws
```

- 默认 `--workspace` 为包内 `workspace/`（需先对该路径 `init-workspace`）。
- `--debug-print-system`：打印本轮拼接后的 system prompt（验收「MEMORY 是否进 system」）。
- **`inty_v2.log`（loguru）**：与 `llm_trace.jsonl` 并列的**运行时日志**（编排、工具结果摘要、记忆线程异常等）。默认写入 `<workspace>/inty_v2.log`；`--no-log-file` 仅 stderr；`--log-file PATH` 指定路径；环境变量 `INTY_V2_PROTO_LOG_FILE` 可设为 `0` / `false` / `no` / `none` 关闭文件，或设为绝对/相对路径覆盖默认。
- **`--llm-trace-file`**：可选 JSONL，记录每轮 `chat.completions` 的请求/响应**摘要**（与 `inty_v2.log` 互补，非完整 prompt 正文）。

## Workspace 结构

| 路径 | 说明 |
|------|------|
| `IDENTITY.md` / `SOUL.md` / `USER.md` / `MEMORY.md` | 人格与长期记忆定稿；`SOUL.md` 在每轮记忆管线末尾由 LLM 策展同步（边界与价值观），下一轮 system 即加载 |
| `AGENTS.md` / `TOOLS.md` / `HEARTBEAT.md` | 可选；若存在则注入 system prompt（有单文件长度上限） |
| `transcript.jsonl` | 每行 JSON：`role`（user \| assistant）、`content`、`ts` |
| `context.json` | 可选：`context_mode`、`user_id`、`companion_id`、`chat_id` |
| `memory/YYYY-MM-DD.md` | 日记层（每轮追加一行摘要）；**当日**文件若存在还会整段注入（有长度上限） |
| `generated_images/` | REPL 调用 `generate_image` 成功且返回体含像素数据时，工具会在此写入一份本地副本（便于本机打开；主结果仍经 GCS 公开 URL） |
| `inty_v2.log` | 默认启用：loguru 文件日志（轮转与保留见 `proto_log.py`）；可用 CLI/`INTY_V2_PROTO_LOG_FILE` 关闭或改路径 |

## 自测（对应原型 §8）

1. **续聊**：`repl` 中对话若干轮后退出，再次启动同一 `--workspace`，应能依赖 `transcript.jsonl` 接续上下文。
2. **记忆**：编辑 `MEMORY.md` 或依赖每轮后的记忆精炼（LLM 覆盖 `MEMORY.md`，并同步策展 `SOUL.md`）。`run_turn` 在返回前会**同步**跑完该管线，下一轮输入即加载新 `SOUL.md`（代价是每轮多几次 LLM 调用、耗时更长）。`--debug-print-system` 可验收 SOUL/MEMORY 是否进 system。
3. **无 DB**：代码中不 import `sqlalchemy`、`psycopg` 等。
4. **单一写入**：助手消息追加到 `transcript.jsonl` 仅出现在 `orchestrator.py`（`memory_update` 不写 assistant 行）。
5. **生图（可选）**：配置 Fal + GCS 后，在 `repl` 中明确向助手要图；工具成功后检查 `generated_images/` 是否出现新文件，或阅读工具返回的 `gcs_http_url=` 摘要（无需把 URL 写进验收文档）。

## 刻意不实现

无 HTTP、无流式、无 try/except 兜底、无幂等与并发控制（见原型文档）。
