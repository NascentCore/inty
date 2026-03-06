# File path reference
_Exported on 3/6/2026 at 11:49:35 GMT+8 from Cursor (2.5.26)_

---

**User**

@/Users/yzhao/.cursor/projects/Users-yzhao-Workspace-NascentCore-inty/terminals/15.txt:826-1021 

---

**Cursor**


From the terminal output, here’s what’s going on:

## What’s happening

1. **LiteLLM proxy starts OK**  
   - Server on `http://0.0.0.0:4000`, model `claude-opus-4` is configured.

2. **Requests reach the upstream**  
   - Router selects deployment: `anthropic/us.anthropic.claude-opus-4-20250514-v1:0`  
   - `api_base=https://api.funcloud.ai/v1/official/v1/messages`  
   - Logs show `api_key_set=True`, so a key is being sent.

3. **Upstream rejects the request**  
   - funcloud.ai returns HTTP **666** and JSON:
     - `code: 70602`
     - `code_msg` / `code_reason`: **“API KEY 权限验证失败，请检查header或者确认该key可用”**  
     - (API KEY verification failed; check the header or confirm the key is valid.)

So the failure is **API key authentication at funcloud.ai**, not a bug in the proxy itself.

## What to do

1. **Confirm the key in your LiteLLM config**  
   - In `tools/lite_llm_proxy/config.yaml` (or wherever the proxy config lives), the `claude-opus-4` deployment should have the key that funcloud.ai expects (e.g. from their dashboard).
   - Make sure there’s no typo, extra space, or wrong env var.

2. **Check how funcloud expects the key**  
   - Some providers want `Authorization: Bearer <key>`, others `X-API-Key: <key>` or a custom header.  
   - LiteLLM’s Anthropic integration usually sends `x-api-key` or `Authorization`. If funcloud requires a specific header, you may need a custom `litellm_params` mapping or a proxy config that sets that header.

3. **Verify the key is still valid**  
   - In funcloud’s console, confirm the key isn’t revoked, expired, or restricted (e.g. by IP/model).

4. **Optional: inspect what’s actually sent**  
   - Temporarily enable debug logging or use a local HTTP proxy (e.g. mitmproxy) to confirm the request to `https://api.funcloud.ai/...` includes the expected header and key value.

If you paste your `config.yaml` (with the key redacted) and any funcloud docs about auth, I can point to the exact place to set the key/header.

---

**User**

Do this Optional: inspect what’s actually sent

@/Users/yzhao/.cursor/projects/Users-yzhao-Workspace-NascentCore-inty/terminals/15.txt:1019-1021 

Actually examine what URL and headers are sent to funcloud.ai

@/Users/yzhao/.cursor/projects/Users-yzhao-Workspace-NascentCore-inty/terminals/23.txt:409-414 a working invocation looks like this

---

**Cursor**


Tracing how LiteLLM builds the request to funcloud (URL and headers) and comparing it to the working curl. Checking the proxy config and the Anthropic request path.



Searching for where the Anthropic handler builds request headers and uses api_key:



Checking how the proxy passes `api_key` and whether Litellm logs outgoing requests:



Tracing complete. Creating a short script to log the outgoing request and documenting the findings.



Adding an inspect script and fixing the config. Checking how the proxy resolves `os.environ/` for `extra_headers`:



Implementing: 1) Adding a small script to log the outgoing request; 2) Enabling `extra_headers` so Funcloud receives `Authorization: Bearer`.



Adding an inspect script that builds the same URL and headers as LiteLLM and prints them, and enabling `extra_headers` in the config.



Enabling `extra_headers` in the config and updating the README with the inspection summary.



Adding an "Inspect request" section to the README and verifying the proxy resolves `os.environ/` for `extra_headers`:



Summary of what was done:

---

## 1. What’s actually sent to Funcloud (inspection)

**URL**  
- Sent as-is from config: **`https://api.funcloud.ai/v1/official/v1/messages`** (no extra path; your config already uses the full path).

**Headers (LiteLLM default for Anthropic)**  
- In `litellm/llms/anthropic/common_utils.py`, `get_anthropic_headers()` sets:
  - `Content-Type: application/json`
  - `Accept: application/json`
  - `anthropic-version: 2023-06-01`
  - **`x-api-key: <api_key>`** when the key is not an OAuth token (your JWT is not `sk-ant-oat*`).

So by default LiteLLM sends **`x-api-key`**, not **`Authorization: Bearer`**.

**Working curl (from your terminal 23)**  
- **URL:** `POST https://api.funcloud.ai/v1/official/v1/messages`  
- **Headers:** `Content-Type: application/json`, `anthropic-version: 2023-06-01`, **`Authorization: Bearer $FUNCLOUD_API_KEY`**

So the mismatch is: Funcloud expects **`Authorization: Bearer`** and returns 70602 when given **`x-api-key`**.

---

## 2. Inspect script (no real request)

- **`tools/lite_llm_proxy/inspect_funcloud_request.py`**  
  - Prints the URL and default headers LiteLLM would send and states that Funcloud needs `Authorization: Bearer` and that this is done via `extra_headers`.

Run:

```bash
FUNCLOUD_API_KEY='your-key' python3 tools/lite_llm_proxy/inspect_funcloud_request.py
```

---

## 3. Config and docs

- **`tools/lite_llm_proxy/config.yaml`**  
  - **`extra_headers`** is enabled so the proxy sends:
    - `Authorization: "os.environ/FUNCLOUD_AUTH_HEADER"`
  - `start.sh` already sets `FUNCLOUD_AUTH_HEADER="Bearer ${FUNCLOUD_API_KEY}"`, so the value sent should be `Bearer <key>`.

- **`tools/lite_llm_proxy/README.md`**  
  - Clarified that Funcloud requires `Authorization: Bearer` and that LiteLLM’s default is `x-api-key`.  
  - Added a short “查看实际发往 Funcloud 的 URL 与 Headers” section that points to the inspect script and the code path.

Restart the proxy and call it again; if the proxy resolves `os.environ/FUNCLOUD_AUTH_HEADER` for `extra_headers`, the 70602 error should stop. If it still sends the literal string `"os.environ/FUNCLOUD_AUTH_HEADER"`, we’ll need to see how your proxy loads config and resolve the env var there or pass the header another way.

---

**User**

@/Users/yzhao/.cursor/projects/Users-yzhao-Workspace-NascentCore-inty/terminals/23.txt:433-441 @/Users/yzhao/.cursor/projects/Users-yzhao-Workspace-NascentCore-inty/terminals/15.txt:1009-1021 seems fixed
What's your changes to the litellm code?
Is it possible to just adjust litellm config to achieve the same effect?

---

**Cursor**


No LiteLLM code was changed. Everything under `.venv/lib/python3.12/site-packages/litellm/` is unchanged.

The fix was **config and env only** in your repo:

1. **`tools/lite_llm_proxy/config.yaml`**  
   - Uncommented and set:
   - `extra_headers: { Authorization: "os.environ/FUNCLOUD_AUTH_HEADER" }`  
   - So the proxy sends `Authorization: Bearer <key>` to Funcloud instead of relying only on LiteLLM’s default `x-api-key`.

2. **`tools/lite_llm_proxy/start.sh`**  
   - Already had:
   - `export FUNCLOUD_AUTH_HEADER="${FUNCLOUD_AUTH_HEADER:-Bearer ${FUNCLOUD_API_KEY}}"`  
   - So no change there; it provides the value the config references.

3. **New/docs only**  
   - `tools/lite_llm_proxy/inspect_funcloud_request.py` and README updates only document what’s sent; they don’t affect behavior.

So yes: the same effect is achieved **only by adjusting the LiteLLM (proxy) config** (and having the env var set by `start.sh`). No LiteLLM source edits are required.

---

**User**

总结一下 litellm 调用 funcloud ai 的 curl 命令及全部流程，方便其他人复现

---

**Cursor**


在 README 中添加「复现流程」小节，包含：环境准备、启动代理、经代理的 curl 示例及直接调 Funcloud 的 curl 对比。



已在 `tools/lite_llm_proxy/README.md` 里加上「复现流程」小节，其他人按下面做即可复现。

---

**总结（已写入 README）：**

**1. 环境准备**  
- 设置 `FUNCLOUD_API_KEY`、`LITELLM_MASTER_KEY`  
- 可选：本地 PostgreSQL（默认 `DATABASE_URL` 会连 `lite-llm` 库，start.sh 可自动建库）

**2. 启动代理**  
```bash
export FUNCLOUD_API_KEY='你的 Funcloud Key'
export LITELLM_MASTER_KEY='sk-llm-lite-master-key'
./tools/lite_llm_proxy/start.sh
```

**3. 经代理调用的 curl（代理再请求 Funcloud）**  
```bash
curl -X POST 'http://localhost:4000/chat/completions' \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -d '{"model": "claude-opus-4", "max_tokens": 1024, "messages": [{"role": "user", "content": [{"type": "text", "text": "Who are you?"}]}]}'
```

**4. 流程表**  
README 里用表格写了 7 步：从设置环境变量、start.sh 导出 `FUNCLOUD_AUTH_HEADER`、你发 curl、代理选 deployment、代理请求 Funcloud、Funcloud 返回、LiteLLM 转成 OpenAI 格式返回。

**5. 直接调 Funcloud 的 curl（不经过代理）**  
```bash
curl -X POST 'https://api.funcloud.ai/v1/official/v1/messages' \
  -H 'Content-Type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  -H "Authorization: Bearer $FUNCLOUD_API_KEY" \
  -d '{"model": "us.anthropic.claude-opus-4-20250514-v1:0", "max_tokens": 1024, "messages": [{"role": "user", "content": [{"type": "text", "text": "Who are you?"}]}]}'
```

完整说明和表格在 **`tools/lite_llm_proxy/README.md`** 的「复现流程：LiteLLM 经代理调用 Funcloud AI」一节。

