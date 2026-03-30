# INTY v2 本地文本聊天原型

依据仓库文档 `docs/INTY_v2_CORE_AGENTIC_COMPONENT_TECH_PROTOTYPE.md`：单进程 CLI、Markdown + JSONL 文件持久化、**无 HTTP、无数据库**。与 `docs/INTY_v2_CORE_AGENTIC_COMPONENT_TECH_ARCHITECTURE.md` **§3（编排）**、**§20（单一写入路径）** 对齐：助手对用户可见文本仅通过 `orchestrator.run_turn` 追加到 `transcript.jsonl`。脑启发式多层记忆总结器方案见 `../../../researches/brain_inspired_memory_summarizer/FR_BRAIN_INSPIRED_MEMORY_LAYER_SUMMARIZER.md`。

## 依赖

本目录 [requirements.txt](requirements.txt)（`cyclopts`、`langsmith`、`openai`、`pydantic`、`python-dotenv`、`loguru`、`PyYAML`）。`generate_image` 会导入 `app.core.config`（读仓库根 `config.yaml`），因此需要 **PyYAML** 与下文所述的仓库根依赖。建议在 `inty` 仓库根虚拟环境中安装：

```bash
cd /path/to/inty
uv pip install -r experimental/inty_v2_text_chat_prototype/requirements.txt
```

REPL 的 **`generate_image`**（Fal **z-image-turbo** 文生图）复用 [`app/core/images/fal.py`](../../app/core/images/fal.py)；模型按对话在工具参数中填写 `num_images`（默认 1，单次上限 4）。需在同一 venv 中安装**仓库根** [`requirements.txt`](../../requirements.txt)（含 `fal-client`、GCS 等）。

**Fal 与 GCS：统一用仓库根 `config.yaml`（与后端一致）**，在**从 `inty/` 目录运行**时由 `app.core.config` 加载；导入后端模块时会将 `fal.api_key` 同步到进程环境变量 `FAL_KEY`（供 `fal_client` 使用），因此**不要**再依赖单独设置 `FAL_KEY` 作为唯一来源。至少配置：

- **`fal.api_key`** — 与 [Fal 文档](https://fal.ai/docs) 一致，格式同生产 [`devops/config.yaml.prod`](../../devops/config.yaml.prod) 中的 `fal:` 段。
- **`gcs`** — 例如 `bucket`；真实上传需 **`app.gcp_service_account_key`** 指向可写该 bucket 的服务账号 JSON（路径相对仓库根）。本地可自 `devops/config.yaml.test` 复制为 `config.yaml` 再改：测试模板常开 `gcs.use_fake_gcs`，若仍要联调真实 Fal，通常需关闭 fake 并补齐 `fal.api_key` 与可写 bucket（测试 YAML 里可能未写 `fal:`，需自行追加该段）。

**可选环境变量（仅原型）：** `INTY_V2_PROTO_Z_IMAGE_GCS_BASE` — 覆盖 GCS 对象路径前缀；不设则为 `inty_v2_proto_chat_images/<workspace 目录名>`。`INTY_V2_PROTO_Z_IMAGE_SKIP_GCS=1`（或 `true`/`yes`/`on`）— **跳过对生成结果的 GCS 上传**，仅保留 Fal 返回的像素数据与 `generated_images/` 本地副本（省掉解析/压缩/上传延迟；工具摘要里 `gcs_http_url` 为空）。**`modify_image` 若使用 workspace 内源图文件**，仍须先把该源图上传到 GCS 以得到 Fal 可用的 `image_url`（与是否跳过**输出**上传无关）；若只用公网 `source_image_url` 则无需上传源图。

**聊天 LLM（与 `config.yaml` 无关）：** `client.get_client()` 固定使用 **OpenRouter** 端点 `https://openrouter.ai/api/v1`，**只**读取 `OPENROUTER_API_KEY`（不再使用 `OPENAI_API_KEY` 或直连 OpenAI base URL）。若你过去只配了 `OPENAI_API_KEY`，请改为在 [OpenRouter](https://openrouter.ai/) 创建 key 并写入 `OPENROUTER_API_KEY`；模型名仍用 OpenRouter 前缀（如 `openai/gpt-4o-mini`）。建议把 key 放在 **`inty` 仓库根** 的 `.env`（与 `config.yaml` 同级）；`main` / `client` 会先加载该 `.env` 再加载当前工作目录下的 `.env`，因此在子目录里执行 `python main.py` 也能读到。勿将 `.env` 提交到 git。

**LangSmith（可选）：** `client` 使用 [`wrap_openai`](https://docs.langchain.com/langsmith/trace-openai)。须设置 `LANGSMITH_API_KEY`（或兼容的 `LANGCHAIN_API_KEY`），并把 **`LANGSMITH_TRACING=true` 或 `LANGSMITH_TRACING_V2=true`** 写成字面量 **`true`**（小写）；`1`、`True`、`.env` 里的大写 `True` 等值可能被 SDK 视为未开启。可选 `LANGSMITH_PROJECT`（默认在 LangSmith 里多为 `default` 项目）。进程退出前会 `flush` 缓存 client，避免 `once` 等短进程丢末批 trace。

无上述 Fal/GCS 条件时，模型仍可对话，但调用 `generate_image` 会返回以 `ERROR:` 开头的工具结果。

**`google_web_search`（Google Custom Search JSON API）：** REPL 工具侧可调用公开网页检索。建议按下面顺序配置（与 GCP 控制台 + Programmable Search Engine 后台一致）：

1. **Google Cloud：** 在目标项目中启用 **Custom Search API**，并创建可调用该 API 的 **API key**（限制为 Custom Search API，勿提交到 git）。
2. **Programmable Search Engine：** 在 [控制面板](https://programmablesearchengine.google.com/) 创建引擎；在 **Overview** 页复制 **Search engine ID**（即 Custom Search 请求参数 **`cx`**）。若要做**全网**检索而非限定站点，在 **Search features** 中打开 **Search the entire web**（仅列站点时结果会受限于白名单）。
3. **环境变量**（写入仓库根 `.env`，勿入库）：
   - **`GOOGLE_CSE_API_KEY`** — 上一步 GCP API key。
   - **`GOOGLE_CSE_ID`** — 上一步 Overview 中的 Search engine ID（`cx`）。

Google 曾在控制台提示：依赖「Search the entire web」的**全网搜索能力**可能有产品层面的调整（例如曾公告相关能力于 **2027-01-01** 起变更）；若你依赖全网检索，请届时查阅 [Custom Search / PSE 官方文档](https://developers.google.com/custom-search) 并评估迁移。

免费档约 **100 次查询/日**（以 Google 文档为准）。需安装仓库根 [`requirements.txt`](../../requirements.txt) 中的 **`httpx`**（与后端一致）。未配置时工具返回以 `ERROR:` 开头的说明。

## 运行方式

在 **`inty/` 目录下**执行（保证 `experimental` 包可解析）：

```bash
cd /path/to/inty
export OPENROUTER_API_KEY=...   # 须为 OpenRouter 的 key（见上文）
export INTY_V2_PROTO_MODEL=openai/gpt-4o-mini   # 可选；记忆精炼可用 INTY_V2_PROTO_MEMORY_MODEL
# 异步工具后台（默认开启；显式关闭：INTY_V2_PROTO_ASYNC_TOOL_BG=0）：
# 前台先跑无 tools 的 chat，立即返回并落 transcript(source=chat)；工具路在同轮快照上后台执行，
# 若有 tool_calls，结束后再追加 transcript(source=tool_bg) 并投递 REPL 事件；若无 tool_calls 则不追加。
# 开启时 run_turn 走该路径，不再使用下面的「双路并行」同步 tool loop。
# 可选：双路并行 LLM（仅当 INTY_V2_PROTO_ASYNC_TOOL_BG=0 时生效；聊天低延迟 + 工具强调用）：
#   INTY_V2_PROTO_DUAL_LLM=1
#   INTY_V2_PROTO_CHAT_MODEL=openai/gpt-4o-mini      # 聊天路（不挂工具）
#   INTY_V2_PROTO_TOOL_MODEL=openai/gpt-4.1-mini     # 工具路（挂工具）
# 两路每轮使用同一份上下文快照并并发调用；两路 assistant 输出会持续并入同一轮历史，再由工具路推进 tool loop。
# 可选：SOUL.md 策展（默认与 MEMORY 同模型）；关闭自动写 SOUL：INTY_V2_PROTO_SOUL_UPDATE_DISABLED=1
# 当日总结（memory/YYYY-MM-DD.md）LLM：默认每 100 次记忆管线调用跑一次；改频率：INTY_V2_PROTO_DAY_SUMMARY_EVERY_N_TURNS=1（每轮）；关闭：INTY_V2_PROTO_DAY_SUMMARY_DISABLED=1
# USER.md 策展 LLM：默认同样每 100 次记忆管线调用一次（与当日总结共用 turns_completed）；每轮：INTY_V2_PROTO_USER_UPDATE_EVERY_N_TURNS=1；关闭：INTY_V2_PROTO_USER_UPDATE_DISABLED=1

python -m experimental.inty_v2_text_chat_prototype.main init-workspace --path ./experimental/inty_v2_text_chat_prototype/_ws
python -m experimental.inty_v2_text_chat_prototype.main repl --workspace ./experimental/inty_v2_text_chat_prototype/_ws
python -m experimental.inty_v2_text_chat_prototype.main once --message "你好" --workspace ./experimental/inty_v2_text_chat_prototype/_ws
```

- 默认 `--workspace` 为包内 `workspace/`（需先对该路径 `init-workspace`）。
- `--debug-print-system`：打印本轮拼接后的 system prompt（验收「MEMORY 是否进 system」）。
- **`inty_v2.log`（loguru）**：与 `llm_trace.jsonl` 并列的**运行时日志**（编排、工具结果摘要、记忆线程异常等）。默认只写入 `<workspace>/inty_v2.log`、**不**打到终端，避免干扰 REPL；`--no-log-file` 或 `INTY_V2_PROTO_LOG_FILE=0` 时改为仅 stderr；`--log-file PATH` 指定路径；`INTY_V2_PROTO_LOG_FILE` 也可设为绝对/相对路径覆盖默认。文件 sink 默认级别为 **DEBUG**（含 `run_turn` / 记忆管线 / `complete` 的体量与预览等）；若只要 INFO 及以上，可设 `INTY_V2_PROTO_LOG_FILE_LEVEL=INFO`。
- **`llm_trace.jsonl`**：`repl` / `once` / `bootstrap-agent` 默认追加写入 `<workspace>/llm_trace.jsonl`，记录每轮 `chat.completions` 的请求/响应**摘要**（与 `inty_v2.log` 互补，非完整 prompt 正文）；可用 `tail -f` 或 `jq` 过滤。
- **REPL 无阻塞输入**：在 **macOS/Linux 交互式 TTY** 上，`run_turn`（含生图等长耗时工具）在**工作线程**跑，**主线程**用 `select`+`readline` 把后续行写入队列，生图时也可先敲好下一行（FIFO）。**Windows / 非 TTY** 仍用 `app.core.repl_input.spawn_stdin_line_reader` 守护线程读 stdin。
- **陪伴心跳（REPL）：** 设 `INTY_V2_PROTO_HEARTBEAT=1` 或 `repl --repl-heartbeat`，在**上一轮助手已回复、你尚未输入**且空闲超过节奏阈值时，自动多跑一轮「主动开口」（不写入记忆管线；`transcript` 里用户行带 `heartbeat: true`）。该轮送入模型的**近期对话窗口**与普通轮相同（最后 `TRANSCRIPT_WINDOW_MAX_MESSAGES` 条），便于口吻与现场气氛一致。可调：`INTY_V2_PROTO_HEARTBEAT_IDLE_SEC`（默认 120）、`INTY_V2_PROTO_HEARTBEAT_MIN_GAP_SEC`（两次心跳最小间隔，默认 600）、`INTY_V2_PROTO_HEARTBEAT_MIN_TRANSCRIPT_MSGS`（至少几条消息才启用，默认 2）。`--no-repl-heartbeat` 优先关闭。

## Workspace 结构

| 路径 | 说明 |
|------|------|
| `IDENTITY.md` / `SOUL.md` / `USER.md` / `MEMORY.md` | 人格与长期记忆定稿；`MEMORY`/`SOUL` 由 LLM 每轮在记忆管线中策展；`USER.md` 的 LLM 策展默认每 100 轮一次（与 `INTY_V2_PROTO_USER_UPDATE_EVERY_N_TURNS` 一致；`user_profile_record` 仍可随时追加） |
| `AGENTS.md` / `TOOLS.md` / `HEARTBEAT.md` | 可选；若存在则注入 system prompt（有单文件长度上限） |
| `transcript.jsonl` | 每行 JSON：`role`（user \| assistant）、`content`、`ts`；当前轮写入的 user/assistant 行含同一个 `trace_id`（可关联到 `llm_trace.jsonl` 同轮请求摘要）；assistant 行另含 `source`（`chat` 或 `tool_bg`）与 `reply_to`（被回复的 user 行 `uuid`） |
| `context.json` | 可选：`context_mode`、`user_id`、`companion_id`、`chat_id` |
| `memory/YYYY-MM-DD.md` | 日记层（每轮追加一行摘要）；**当日**文件若存在还会整段注入（有长度上限） |
| `generated_images/` | REPL 调用 `generate_image` 成功且返回体含像素数据时，工具会在此写入一份本地副本（便于本机打开；未设 `INTY_V2_PROTO_Z_IMAGE_SKIP_GCS` 时摘要里另有 GCS 公开 URL） |
| `inty_v2.log` | 默认启用：loguru 文件日志（轮转与保留见 `proto_log.py`）；可用 CLI/`INTY_V2_PROTO_LOG_FILE` 关闭或改路径 |
| `llm_trace.jsonl` | 默认追加：`repl` / `once` / `bootstrap-agent` 每轮 LLM 调用摘要（JSONL） |

## 自测（对应原型 §8）

1. **续聊**：`repl` 中对话若干轮后退出，再次启动同一 `--workspace`，应能依赖 `transcript.jsonl` 接续上下文。
2. **记忆**：编辑 `MEMORY.md` 或依赖记忆管线（`repl` 默认后台队列；`once` 在进程退出前跑完）：`MEMORY.md`、`USER.md`、`SOUL.md` 的 LLM 策展默认均为每 **100** 轮一次（可用 `INTY_V2_PROTO_MEMORY_UPDATE_EVERY_N_TURNS` 等环境变量调整；设为 **1** 即每轮）。`--debug-print-system` 可验收进 system 的段落。
3. **无 DB**：代码中不 import `sqlalchemy`、`psycopg` 等。
4. **单一写入**：助手消息追加到 `transcript.jsonl` 仅出现在 `orchestrator.py`（`memory_update` 不写 assistant 行）。
5. **生图（可选）**：在仓库根 `config.yaml` 配好 `fal.api_key` 与 GCS 后，在 `repl` 中明确向助手要图；工具成功后检查 `generated_images/` 是否出现新文件，或阅读工具返回的 `gcs_http_url=` 摘要（无需把 URL 写进验收文档）。

## 刻意不实现

无 HTTP、无流式、无 try/except 兜底、无幂等与并发控制（见原型文档）。
