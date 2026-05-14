"""Imagen 4.0 超分工具 CLI 入口。"""

from __future__ import annotations

from pathlib import Path

import cyclopts

from tools.upscaler.vertex_imagen import (
    DEFAULT_COMPRESSION_QUALITY,
    DEFAULT_MODEL_ID,
    DEFAULT_OUTPUT_MIME_TYPE,
    DEFAULT_PROMPT,
    DEFAULT_REGION,
    DEFAULT_TIMEOUT_SECONDS,
    UpscaleError,
    VertexUpscaleRequest,
    upscale_image_with_vertex,
)
from tools.upscaler.web_ui import WebServerConfig, run_web_ui

DEFAULT_WEB_HOST = "127.0.0.1"
DEFAULT_WEB_PORT = 8787
MIME_TYPE_TO_EXTENSION = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}

app = cyclopts.App(help="本地图片超分工具（Vertex AI Imagen 4.0）")


def _resolve_output_path(
    *, input_path: Path, output_path: str | None, output_mime_type: str
) -> Path:
    if output_path:
        return Path(output_path)
    suffix = MIME_TYPE_TO_EXTENSION.get(output_mime_type, ".png")
    return input_path.with_name(f"{input_path.stem}_upscaled{suffix}")


@app.command
def serve(host: str = DEFAULT_WEB_HOST, port: int = DEFAULT_WEB_PORT) -> None:
    """启动本地 Web UI。"""

    run_web_ui(WebServerConfig(host=host, port=port))


@app.command
def upscale(
    input_path: str,
    project_id: str,
    api_key: str | None = None,
    output_path: str | None = None,
    access_token: str | None = None,
    region: str = DEFAULT_REGION,
    model_id: str = DEFAULT_MODEL_ID,
    prompt: str = DEFAULT_PROMPT,
    upscale_factor: str = "x2",
    output_mime_type: str = DEFAULT_OUTPUT_MIME_TYPE,
    compression_quality: int = DEFAULT_COMPRESSION_QUALITY,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> None:
    """纯命令行单次超分。"""

    source_path = Path(input_path)
    if not source_path.exists() or not source_path.is_file():
        raise ValueError(f"输入文件不存在: {source_path}")

    request_data = VertexUpscaleRequest(
        project_id=project_id,
        api_key=api_key,
        access_token=access_token,
        region=region,
        model_id=model_id,
        prompt=prompt,
        upscale_factor=upscale_factor,
        output_mime_type=output_mime_type,
        compression_quality=compression_quality,
        timeout_seconds=timeout_seconds,
        image_bytes=source_path.read_bytes(),
    )
    result = upscale_image_with_vertex(request_data)
    target_path = _resolve_output_path(
        input_path=source_path,
        output_path=output_path,
        output_mime_type=result.mime_type,
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(result.image_bytes)
    print(f"超分完成: {target_path} ({result.mime_type})")


def main() -> int:
    try:
        return int(app())
    except UpscaleError as exc:
        print(f"超分失败: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
