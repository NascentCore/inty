# 图片超分工具（tools/upscaler）

本工具使用 Python 实现，支持：

1. 命令行使用
2. 本地 Web UI 使用
3. 从 `tools/upscaler/.env` 读取 API Key 与 Project ID
4. 默认使用 Vertex AI Imagen 4.0 Upscale（`imagen-4.0-upscale-preview`）
5. 参考文档：<https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/imagen/4-0-upscale?hl=en>

## 配置

复制 `tools/upscaler/.env.example` 为 `tools/upscaler/.env`，填入 `GOOGLE_CLOUD_VERTEX_AI_API_KEY` 与 `GOOGLE_CLOUD_PROJECT_ID`。

## 启动 Web UI（本地）

```bash
uv venv
source .venv/bin/activate
uv run -m tools.upscaler.main serve --host 127.0.0.1 --port 8787
```

浏览器打开：<http://127.0.0.1:8787>

在页面中可调整 Region、Model ID、Upscale Factor 等。上传图片后点击开始超分即可。


## 纯命令行方式

```bash
python3 -m tools.upscaler.main upscale \
  --input-path ./input.png \
  --project-id your-gcp-project-id \
  --api-key "$GOOGLE_API_KEY" \
  --upscale-factor x2
```

可选参数：

- `--output-path`：输出路径（默认自动生成 `<原文件名>_upscaled.<ext>`）
- `--access-token`：Bearer Token
- `--output-mime-type`：`image/png` / `image/jpeg` / `image/webp`
- `--compression-quality`：0-100（默认 75）
- `--timeout-seconds`：请求超时时间

## 实现说明

- 默认请求 Vertex REST endpoint：
  - `POST https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/publishers/google/models/imagen-4.0-upscale-preview:predict`
- 请求 `parameters.mode=upscale`
- 支持 `upscaleConfig.upscaleFactor`：`x2` / `x3` / `x4`

## 补充说明

- 只能使用 vertex ai API key（而非 Google AI studio API key）
  <img width="800" height="1804" alt="image" src="https://github.com/user-attachments/assets/3d185f30-186b-4619-acb0-6166af3904e3" />
