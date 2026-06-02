# AI Local Playground

<!-- CREATED_BY_AGENT -->

本地聚合 Web UI + FastAPI：在同一页面试用 **OpenRouter 文本模型**、**fal GPT Image 1.5 edit**、**Vertex Nano Banana** 等。

## 前置条件

- 仓库根目录可导入 `app`（`PYTHONPATH=.`）
- Inty 配置文件（Gemini / GCS）：`config.yaml` 或 `devops/config.yaml.local`
- 环境变量：
  - `OPENROUTER_API_KEY`（或 `OPENAI_API_KEY`）— 文本
  - `FAL_KEY` — fal 生图（含 `fal-ai/gpt-image-1.5/edit`）
  - Vertex 凭证由 `config.yaml` 的 GCP 配置提供 — Nano Banana

可复制 [.env.example](.env.example) 到仓库根 `.env` 后 `source` 或 `export`。

## 启动

在仓库根目录：

```bash
export OPENROUTER_API_KEY=sk-or-v1-...
export FAL_KEY=...

# 若尚无 config.yaml：
cp devops/config.yaml.local config.yaml

PYTHONPATH=. python -m tools.ai_local_playground.main serve --config devops/config.yaml.local
```

浏览器打开：<http://127.0.0.1:8777/>

可选参数：`--host`、`--port`（默认 `127.0.0.1:8777`）。

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 密钥与 config 路径 |
| GET | `/api/models` | 下拉模型列表 |
| POST | `/api/text` | OpenRouter chat |
| POST | `/api/image` | Gemini 或 fal 生图 |

实现复用：`app/external_services/text_to_image.py`、`app/core/google_genai/wrapped_client.py`、`app/core/companion_harness/llm/chat_completions.py`。

## 模型说明

- **Text**：`CHAT_TEXT_MODELS`（DeepSeek、Gemini Flash 等），亦支持直接填 OpenRouter model id。
- **Image — Nano Banana**：`gemini-2.5-flash-image`、`gemini-3-pro-image-preview`、`gemini-3.1-flash-image-preview` 等；可选参考图 URL（每行一个）。
- **Image — GPT Image**：选 `GPT Image 1.5 Edit (fal)`，需 `image_urls`；`input_fidelity` 为 `low` / `high`。
- **Image — 其他 fal**：Seedream edit、Z Image turbo 等见下拉列表。
