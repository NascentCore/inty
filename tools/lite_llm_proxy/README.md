# LiteLLM On-Prem Proxy for OpenRouter

This folder provides a copy-paste setup for running an on-prem LiteLLM proxy that routes requests to OpenRouter, with:

- virtual API key creation (`/key/generate`)
- per-key quota (`max_budget`, `budget_duration`)
- per-key rate limits (`rpm_limit`, `tpm_limit`)
- key expiration (`duration`, including seconds like `604800s`)

## Files

- `.env.example`: required environment variables
- `docker-compose.yml`: LiteLLM + Postgres deployment
- `litellm_config.yaml`: model routing + default/upper-bound key policies
- `key_management_examples.sh`: helper commands for key create/update/info/delete

## 1) Configure env

Create `.env` from template and edit values:

`cp .env.example .env`

Required:

- `LITELLM_MASTER_KEY` (must start with `sk-`)
- `LITELLM_SALT_KEY`
- `POSTGRES_PASSWORD`
- `OPENROUTER_API_KEY`

Optional:

- `OPENROUTER_API_BASE` (defaults to `https://openrouter.ai/api/v1`)
- `OR_SITE_URL`
- `OR_APP_NAME`

## 2) Start services

From this directory:

`docker compose up -d`

Check health:

`docker compose ps`

LiteLLM endpoints:

- Proxy base URL: `http://localhost:4000`
- Admin UI: `http://localhost:4000/ui`

## 3) Generate keys with quota and expiration

Source helper script:

`source ./key_management_examples.sh`

Examples:

- Permanent key (no expiration): `generate_key_permanent`
- 1-week key (seconds): `generate_key_one_week`
- Update existing key limits: `update_key_limits sk-...`
- Inspect key: `get_key_info sk-...`
- List keys: `list_keys`
- Delete key: `delete_key sk-...`

## 4) Make a proxied OpenAI-compatible call

Replace `USER_KEY` first:

`USER_KEY=sk-...`

`curl -sS http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer ${USER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "or-gpt-4o",
    "messages": [{"role":"user","content":"Say hello in one short sentence."}]
  }'`

## Notes

- Keep `LITELLM_MASTER_KEY` private. It can create and manage all proxy keys.
- `duration` and `budget_duration` support units like `s`, `m`, `h`, `d`.
- To enforce org-wide policy, edit `litellm_settings.upperbound_key_generate_params`.

# LiteLLM 代理（Funcloud / Anthropic Claude）

参见 [config.yaml](config.yaml) 与 [start.sh](start.sh)。需配置 `FUNCLOUD_API_KEY`、`LITELLM_MASTER_KEY`，且启用 master-key 时需配数据库。

## 复现流程：LiteLLM 经代理调用 Funcloud AI

### 1. 环境准备

- Python 3.12 + 已安装 `litellm`（或使用 `uv run`）
- 可选：本地 PostgreSQL（若用默认 `DATABASE_URL`，需有 `lite-llm` 库；start.sh 会自动建库）
- 环境变量：
  - `FUNCLOUD_API_KEY`：Funcloud 的 API Key（必填）
  - `LITELLM_MASTER_KEY`：代理鉴权用，客户端请求时需带 `Authorization: Bearer <此 key>`（必填）
  - `DATABASE_URL`：不设则 start.sh 使用默认 `postgresql://postgres:sxwl666!@localhost:5432/lite-llm`

### 2. 启动代理

在仓库根目录执行：

```bash
export FUNCLOUD_API_KEY='你的 Funcloud Key'
export LITELLM_MASTER_KEY='sk-llm-lite-master-key'   # 示例，可自定

./tools/lite_llm_proxy/start.sh
```

代理监听 `http://0.0.0.0:4000`。start.sh 会设置 `FUNCLOUD_AUTH_HEADER="Bearer $FUNCLOUD_API_KEY"`，供 config 中 `extra_headers.Authorization` 使用（Funcloud 只认 Bearer，不认 x-api-key）。

### 3. 用 curl 调用代理（代理再请求 Funcloud）

客户端对**代理**发 OpenAI 兼容的 `/chat/completions`，代理根据 config 将请求转发到 Funcloud `https://api.funcloud.ai/v1/official/v1/messages`，并带上 `Authorization: Bearer $FUNCLOUD_API_KEY`，最后把 Funcloud 的 Anthropic 风格响应转成 OpenAI 风格返回：

```bash
curl -X POST 'http://localhost:4000/chat/completions' \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -d '{
    "model": "claude-opus-4",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": [{"type": "text", "text": "Who are you?"}]}]
  }'
```

成功时返回 OpenAI 格式，例如 `{"id":"chatcmpl-...","object":"chat.completion","choices":[...],"usage":{...}}`。

### 4. 流程小结

| 步骤 | 谁 | 动作 |
|------|----|------|
| 1 | 你 | 设置 `FUNCLOUD_API_KEY`、`LITELLM_MASTER_KEY`，执行 `./tools/lite_llm_proxy/start.sh` |
| 2 | start.sh | 导出 `FUNCLOUD_AUTH_HEADER="Bearer $FUNCLOUD_API_KEY"`，启动 litellm --config config.yaml --port 4000 |
| 3 | 你 | `curl -X POST http://localhost:4000/chat/completions -H "Authorization: Bearer $LITELLM_MASTER_KEY" -d '{"model":"claude-opus-4",...}'` |
| 4 | LiteLLM 代理 | 用 config 中 model_list 的 `claude-opus-4` 对应 deployment：api_base=Funcloud `/v1/official/v1/messages`，extra_headers 提供 `Authorization: Bearer <Funcloud Key>` |
| 5 | LiteLLM | 向 Funcloud 发 POST `https://api.funcloud.ai/v1/official/v1/messages`，Header 含 `Authorization: Bearer $FUNCLOUD_API_KEY`、`anthropic-version: 2023-06-01` 等，body 为 Anthropic messages 格式 |
| 6 | Funcloud | 返回 Anthropic 风格 JSON（type/message/content/usage/stop_reason） |
| 7 | LiteLLM | 将响应转成 OpenAI 风格（choices/usage）返回给 curl |

### 5. 直接 curl 调用 Funcloud（不经过代理）

不经过 LiteLLM 时，可直接请求 Funcloud（需 `Authorization: Bearer $FUNCLOUD_API_KEY`，不能用 x-api-key）：

```bash
curl -X POST 'https://api.funcloud.ai/v1/official/v1/messages' \
  -H 'Content-Type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  -H "Authorization: Bearer $FUNCLOUD_API_KEY" \
  -d '{
    "model": "us.anthropic.claude-opus-4-20250514-v1:0",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": [{"type": "text", "text": "Who are you?"}]}]
  }'
```

返回为 Anthropic 风格（无 `choices`，有 `content`/`usage.input_tokens`/`output_tokens`）。

---

## 直接 curl 调用 Funcloud（参考）

Funcloud 在固定路径下接受 **OpenAI 风格** 请求。正确 URL（已用 tools/llm.py 验证）：

- **Base：** `https://api.funcloud.ai/v1/official`
- **对话路径：** `https://api.funcloud.ai/v1/official/chat/completions`

Funcloud 同时支持 **chat/completions** 与 **v1/messages**（正确路径见下）。

示例（先设置环境变量 `FUNCLOUD_API_KEY`；Funcloud 要求使用 `Authorization: Bearer`，不能用 `x-api-key`）：

```bash
curl -X POST 'https://api.funcloud.ai/v1/official/chat/completions' \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $FUNCLOUD_API_KEY" \
  -d '{
    "model": "us.anthropic.claude-opus-4-20250514-v1:0",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Who are you?"}]
  }'
```

请求体：**OpenAI 风格** 用 `"content": "字符串"`；**Anthropic 风格** 用 `"content": [{"type": "text", "text": "..."}]` 请求 `.../v1/messages` 即可。

## 实测结论（Funcloud 端点行为）

- **请求：** Funcloud 支持两 path：`.../v1/official/chat/completions`（OpenAI 风格，content 为字符串）、`.../v1/official/v1/messages`（Anthropic 风格，content 为 `[{"type":"text","text":"..."}]`）。
- **响应：** 端点返回 **Anthropic 风格** 响应：顶层 `type: "message"`，`content: [{"type":"text","text":"..."}]`，`usage.input_tokens` / `usage.output_tokens`，以及 `stop_reason`（如 `"end_turn"`）。没有 `choices` 数组，也没有 `usage.prompt_tokens` / `completion_tokens`。
- **鉴权：** 必须使用 `Authorization: Bearer $FUNCLOUD_API_KEY`。用 `x-api-key` 传 key 会返回 `{"code":70602,"code_msg":"API KEY 权限验证失败"}`。LiteLLM 默认对 Anthropic 使用 `x-api-key`，故 config 中需用 `extra_headers.Authorization: os.environ/FUNCLOUD_AUTH_HEADER`，由 start.sh 导出 `FUNCLOUD_AUTH_HEADER="Bearer $FUNCLOUD_API_KEY"`。
- **LiteLLM：** 代理默认期望 OpenAI 结构的响应。因 Funcloud 返回 Anthropic 结构 JSON，代理可能报 "Invalid response object" / `assert response_object["choices"] is not None`。若出现此情况，需用 CustomLLM 等 handler 做响应转换（参见 config.yaml 注释及 LiteLLM 自定义 provider 文档）。
- **经本代理调用：** config 已配置 `anthropic/claude-opus-4`，走 Funcloud `/v1/official/v1/messages`。`api_base` 仅填 base（`https://api.funcloud.ai/v1/official`），由 LiteLLM 自动追加 `/v1/messages`（见 [LiteLLM Anthropic 文档](https://docs.litellm.ai/docs/providers/anthropic)）。鉴权通过 `extra_headers.Authorization: Bearer`，由 `start.sh` 设置 `FUNCLOUD_AUTH_HEADER`。客户端请求示例：`model: "anthropic/claude-opus-4"` 或 `model: "us.anthropic.claude-opus-4-20250514-v1:0"`（若代理做了 model 映射）。
- **/v1/models 为空：** 当配置了 `database_url` 时，代理从数据库（`LiteLLM_ProxyModelTable`）提供模型列表。Config 里的 `model_list` **不会**在启动时自动写入 DB；`store_model_in_db: true` 只表示“通过 API/UI 新增或更新的模型会写入 DB”。若 DB 从未写入过模型（如首次运行或新库），表为空，`GET /v1/models` 会返回 `{"data":[],"object":"list"}`。解决办法：用 master key 调用一次 `POST /model/new` 把 config 中的模型写入 DB，或到 Admin UI 添加模型；详见下方“首次同步模型到 DB”。
- **/v1/models 返回 401：** 配置了 `master_key` 后，所有代理端点（包括 `GET /v1/models`）都需要客户端传鉴权。示例：`curl -X GET 'http://localhost:4000/v1/models' -H "Authorization: Bearer $LITELLM_MASTER_KEY"`。

### 查看实际发往 Funcloud 的 URL 与 Headers

LiteLLM 对 Anthropic 的默认行为（见 `litellm/llms/anthropic/common_utils.py` 的 `get_anthropic_headers`）：**URL** 为 config 中的 `api_base`（本配置为 `https://api.funcloud.ai/v1/official/v1/messages`）；**鉴权** 默认使用 `x-api-key`（非 OAuth key 时），而 Funcloud 要求 `Authorization: Bearer`。运行脚本可本地打印上述结论（不发起请求）：

```bash
FUNCLOUD_API_KEY='your-key' python3 tools/lite_llm_proxy/inspect_funcloud_request.py
```

### 首次同步模型到 DB（解决 /v1/models 为空）

在配置了 `database_url` 且 `store_model_in_db: true` 时，需先把 config 中的模型写入 DB，`GET /v1/models` 才会有数据。一次性操作示例（与当前 config 中的 `claude-opus-4` 一致）：

```bash
# 确保代理已启动且 LITELLM_MASTER_KEY、FUNCLOUD_API_KEY 已设置
curl -X POST 'http://localhost:4000/model/new' \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "claude-opus-4",
    "litellm_params": {
      "model": "anthropic/us.anthropic.claude-opus-4-20250514-v1:0",
      "api_base": "https://api.funcloud.ai/v1/official",
      "api_key": "'"$FUNCLOUD_API_KEY"'"
    }
  }'
```

之后 `GET /v1/models` 应返回非空列表。
