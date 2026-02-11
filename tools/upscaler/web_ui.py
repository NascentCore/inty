"""本地 Web UI：上传图片并调用 Vertex Imagen 超分。"""

from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib import parse

from tools.upscaler.vertex_imagen import (
    DEFAULT_MODEL_ID,
    DEFAULT_PROMPT,
    DEFAULT_REGION,
    DEFAULT_VERTEX_IMAGEN_UPSCALE_DOC_URL,
    UpscaleError,
    VertexUpscaleRequest,
    upscale_image_with_vertex,
)

INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Imagen 4.0 图片超分工具</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #f6f8fb; color: #111827; }
    .container { max-width: 920px; margin: 24px auto; background: white; border-radius: 12px; padding: 20px; box-shadow: 0 6px 24px rgba(0,0,0,0.07); }
    h1 { margin-top: 0; font-size: 1.5rem; }
    p.hint { margin-top: 0; color: #4b5563; }
    form { display: grid; gap: 12px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
    label { display: grid; gap: 6px; font-size: 0.92rem; color: #1f2937; }
    input, select, button, textarea { font: inherit; padding: 9px 10px; border-radius: 8px; border: 1px solid #d1d5db; }
    textarea { min-height: 64px; resize: vertical; }
    button { cursor: pointer; background: #2563eb; color: white; border: none; font-weight: 600; }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    .status { min-height: 24px; font-size: 0.9rem; color: #374151; }
    .status.error { color: #b91c1c; }
    .preview img { max-width: 100%; border-radius: 10px; border: 1px solid #e5e7eb; }
    .preview { margin-top: 18px; }
    .download-link { margin-top: 8px; display: inline-block; }
    code { background: #f3f4f6; padding: 2px 4px; border-radius: 4px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Imagen 4.0 本地图片超分工具</h1>
    <p class="hint">
      默认使用 Vertex AI 文档模型：
      <a href="__DOC_URL__" target="_blank" rel="noreferrer noopener">imagen-4.0-upscale-preview</a>
    </p>

    <form id="upscale-form">
      <div class="grid">
        <label>Google API Key
          <input id="apiKey" type="password" placeholder="AIza..." autocomplete="off" />
        </label>
        <label>Access Token（可选）
          <input id="accessToken" type="password" placeholder="ya29..." autocomplete="off" />
        </label>
      </div>

      <div class="grid">
        <label>Project ID
          <input id="projectId" type="text" required placeholder="your-gcp-project-id" />
        </label>
        <label>Region
          <input id="region" type="text" value="__DEFAULT_REGION__" required />
        </label>
        <label>Model ID
          <input id="modelId" type="text" value="__DEFAULT_MODEL_ID__" required />
        </label>
      </div>

      <div class="grid">
        <label>Upscale Factor
          <select id="upscaleFactor">
            <option value="x2" selected>x2</option>
            <option value="x3">x3</option>
            <option value="x4">x4</option>
          </select>
        </label>
        <label>输出格式
          <select id="outputMimeType">
            <option value="image/png" selected>image/png</option>
            <option value="image/jpeg">image/jpeg</option>
            <option value="image/webp">image/webp</option>
          </select>
        </label>
        <label>compressionQuality (0-100)
          <input id="compressionQuality" type="number" min="0" max="100" value="75" />
        </label>
      </div>

      <label>Prompt
        <textarea id="prompt">__DEFAULT_PROMPT__</textarea>
      </label>

      <label>选择原图
        <input id="sourceImage" type="file" accept="image/*" required />
      </label>

      <button id="submitBtn" type="submit">开始超分</button>
      <div id="status" class="status"></div>
    </form>

    <div id="preview" class="preview" hidden>
      <h2>输出结果</h2>
      <img id="resultImage" alt="Upscaled Result" />
      <br />
      <a id="downloadLink" class="download-link" download="upscaled-image">下载图片</a>
    </div>
  </div>

  <script>
    const form = document.getElementById("upscale-form");
    const submitBtn = document.getElementById("submitBtn");
    const statusEl = document.getElementById("status");
    const previewEl = document.getElementById("preview");
    const resultImageEl = document.getElementById("resultImage");
    const downloadLinkEl = document.getElementById("downloadLink");
    const persistedKeys = ["projectId", "region", "modelId", "upscaleFactor", "outputMimeType", "compressionQuality", "prompt"];

    function restorePersistedSettings() {
      for (const key of persistedKeys) {
        const value = localStorage.getItem("upscaler." + key);
        if (value !== null) {
          const element = document.getElementById(key);
          if (element) {
            element.value = value;
          }
        }
      }
    }

    function persistSettings() {
      for (const key of persistedKeys) {
        const element = document.getElementById(key);
        if (element) {
          localStorage.setItem("upscaler." + key, element.value);
        }
      }
    }

    function setStatus(message, isError) {
      statusEl.textContent = message;
      statusEl.classList.toggle("error", Boolean(isError));
    }

    function fileToBase64(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const result = String(reader.result || "");
          const marker = "base64,";
          const idx = result.indexOf(marker);
          if (idx < 0) {
            reject(new Error("读取图片失败：未找到 base64 数据"));
            return;
          }
          resolve(result.slice(idx + marker.length));
        };
        reader.onerror = () => reject(new Error("读取图片失败"));
        reader.readAsDataURL(file);
      });
    }

    function extensionByMimeType(mimeType) {
      if (mimeType === "image/jpeg") return "jpg";
      if (mimeType === "image/webp") return "webp";
      return "png";
    }

    restorePersistedSettings();
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      setStatus("", false);
      previewEl.hidden = true;
      submitBtn.disabled = true;
      persistSettings();

      const imageInput = document.getElementById("sourceImage");
      const file = imageInput.files && imageInput.files[0];
      if (!file) {
        setStatus("请先选择图片。", true);
        submitBtn.disabled = false;
        return;
      }

      try {
        const imageBase64 = await fileToBase64(file);
        const payload = {
          apiKey: document.getElementById("apiKey").value.trim(),
          accessToken: document.getElementById("accessToken").value.trim(),
          projectId: document.getElementById("projectId").value.trim(),
          region: document.getElementById("region").value.trim(),
          modelId: document.getElementById("modelId").value.trim(),
          prompt: document.getElementById("prompt").value.trim() || "Upscale the image",
          upscaleFactor: document.getElementById("upscaleFactor").value,
          outputMimeType: document.getElementById("outputMimeType").value,
          compressionQuality: Number.parseInt(document.getElementById("compressionQuality").value, 10),
          imageBase64
        };

        const response = await fetch("/api/upscale", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const responseBody = await response.json();
        if (!response.ok) {
          throw new Error(responseBody.error || "请求失败");
        }

        const mimeType = String(responseBody.mimeType || "image/png");
        const imageDataUrl = `data:${mimeType};base64,${responseBody.imageBase64}`;
        resultImageEl.src = imageDataUrl;
        const extension = extensionByMimeType(mimeType);
        downloadLinkEl.href = imageDataUrl;
        downloadLinkEl.download = `upscaled.${extension}`;
        downloadLinkEl.textContent = `下载图片 (${mimeType})`;
        previewEl.hidden = false;
        setStatus("超分完成。", false);
      } catch (error) {
        setStatus(error.message || "超分失败", true);
      } finally {
        submitBtn.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


@dataclass(frozen=True, slots=True)
class WebServerConfig:
    host: str = "127.0.0.1"
    port: int = 8787


class UpscalerHandler(BaseHTTPRequestHandler):
    server_version = "ImagenUpscaler/0.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = parse.urlsplit(self.path)
        if parsed.path == "/":
            self._send_index()
            return
        if parsed.path == "/healthz":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not Found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = parse.urlsplit(self.path)
        if parsed.path != "/api/upscale":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not Found"})
            return
        self._handle_upscale()

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_index(self) -> None:
        html = (
            INDEX_HTML.replace("__DOC_URL__", DEFAULT_VERTEX_IMAGEN_UPSCALE_DOC_URL)
            .replace("__DEFAULT_REGION__", DEFAULT_REGION)
            .replace("__DEFAULT_MODEL_ID__", DEFAULT_MODEL_ID)
            .replace("__DEFAULT_PROMPT__", DEFAULT_PROMPT)
        )
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, Any]:
        content_length = self.headers.get("Content-Length", "0")
        body_length = int(content_length)
        raw_body = self.rfile.read(body_length)
        parsed_body = json.loads(raw_body.decode("utf-8"))
        if not isinstance(parsed_body, dict):
            raise ValueError("JSON body 必须是对象")
        return parsed_body

    def _handle_upscale(self) -> None:
        try:
            body = self._read_json_body()
            request_data = _convert_web_payload(body)
            result = upscale_image_with_vertex(request_data)
        except (ValueError, KeyError, json.JSONDecodeError, UpscaleError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self._send_json(
            HTTPStatus.OK,
            {
                "mimeType": result.mime_type,
                "imageBase64": base64.b64encode(result.image_bytes).decode("ascii"),
                "requestUrl": result.request_url,
                "modelId": result.model_id,
            },
        )

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _convert_web_payload(payload: dict[str, Any]) -> VertexUpscaleRequest:
    image_base64 = _get_required_text(payload, "imageBase64")
    try:
        image_bytes = base64.b64decode(image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("imageBase64 不是合法 base64") from exc

    return VertexUpscaleRequest(
        api_key=_get_optional_text(payload, "apiKey"),
        access_token=_get_optional_text(payload, "accessToken"),
        project_id=_get_required_text(payload, "projectId"),
        region=_get_optional_text(payload, "region") or DEFAULT_REGION,
        model_id=_get_optional_text(payload, "modelId") or DEFAULT_MODEL_ID,
        prompt=_get_optional_text(payload, "prompt") or DEFAULT_PROMPT,
        upscale_factor=_get_optional_text(payload, "upscaleFactor") or "x2",
        output_mime_type=_get_optional_text(payload, "outputMimeType") or "image/png",
        compression_quality=_get_optional_int(payload, "compressionQuality", 75),
        image_bytes=image_bytes,
    )


def _get_required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} 不能为空")
    return value.strip()


def _get_optional_text(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} 必须是字符串")
    stripped = value.strip()
    return stripped if stripped else None


def _get_optional_int(payload: dict[str, Any], key: str, default: int) -> int:
    value = payload.get(key)
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise ValueError(f"{key} 必须是整数")


def run_web_ui(config: WebServerConfig) -> None:
    with ThreadingHTTPServer((config.host, config.port), UpscalerHandler) as server:
        print(f"Web UI 已启动: http://{config.host}:{config.port}")
        print(f"默认文档: {DEFAULT_VERTEX_IMAGEN_UPSCALE_DOC_URL}")
        server.serve_forever()

