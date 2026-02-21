"""Limitations of the official LangSmith tracing wrapper for the Google GenAI SDK.

Ref: https://docs.langchain.com/langsmith/trace-with-google-gemini#configure-tracing
Implementation: app.utils.google_genai_client.wrap_google_genai_client_with_langsmith
"""
from __future__ import annotations

# -----------------------------------------------------------------------------
# Official wrapper: langsmith.wrappers.wrap_gemini
# -----------------------------------------------------------------------------
#
# 1. Only generate_content and generate_content_stream are traced
#    - client.models.generate_images (Imagen) is NOT wrapped.
#    - Imagen calls produce no LangSmith run; "full model request" is unavailable
#      unless you add your own @traceable or span around generate_images.
#
# 2. "Model requests" (complete prompts) depend on contents being dict-like
#    - wrap_gemini uses process_inputs=_process_gemini_inputs, which builds
#      "messages" only when each item in contents is a dict (isinstance(content, dict)).
#    - When you pass google.genai.types.Content (Pydantic), the branch that builds
#      messages is skipped; the trace gets raw kwargs and the prompt text may not
#      appear in the UI.
#
# 3. Our mitigation (in google_genai_client)
#    - After wrap_gemini(client), we patch client.models.generate_content and
#      generate_content_stream so that contents are normalized to list-of-dict
#      (via model_dump()) before the LangSmith traceable runs. That way
#      _process_gemini_inputs sees dicts and records full prompts.
#
# 4. Config / multimodal
#    - Config is converted with vars(config) for tracing; "complete prompts" in
#      the docs refer mainly to contents/messages, not necessarily full config.
#    - Multimodal contents (e.g. inline_data images) are only normalized when
#      parts are dict-like; Pydantic Part objects may not serialize fully.
#
# See: app/core/google_genai/todos/LangSmith_full_model_requests_investigation.md
#
# generate_image 已用 LangSmith @traceable 追踪输入与输出摘要（见 AsyncClient.generate_image）。
#


from google import genai
from google.genai import types
from langsmith.run_helpers import traceable

from app.core.google_genai.predefined_configs import GEN_CONTENT_CONFIG_IMAGE_9_16_1K_R_RATED_ROMANCE_DIRECTOR


def _process_inputs_generate_image(
    _self: object, model: str, contents: list[str]
) -> dict:
    """LangSmith process_inputs：只记录 model 与 contents，不记录 client。"""
    return {"model": model, "contents": contents}


def _process_outputs_generate_image(response: object) -> dict:
    """LangSmith process_outputs：只记录响应摘要（候选数、part 类型与字节长），不写入图片二进制。"""
    out: dict = {}
    if response is None:
        return {"status": "none", "candidates_count": 0}
    if hasattr(response, "prompt_feedback") and response.prompt_feedback:
        pf = response.prompt_feedback
        out["prompt_feedback"] = {"block_reason": getattr(pf, "block_reason", None)}
    raw_candidates = getattr(response, "candidates", None)
    if raw_candidates is None:
        candidates = []
    else:
        try:
            candidates = list(raw_candidates)
        except (TypeError, AttributeError):
            candidates = []
    out["candidates_count"] = len(candidates)
    parts_summaries = []
    for c in candidates:
        content = getattr(c, "content", None)
        parts = getattr(content, "parts", None) if content else None
        if not parts:
            parts_summaries.append([])
            continue
        entry = []
        for p in parts:
            if hasattr(p, "inline_data") and p.inline_data:
                data = getattr(p.inline_data, "data", b"")
                size = len(data) if isinstance(data, bytes) else 0
                entry.append({"kind": "inline_data", "size_bytes": size})
            elif hasattr(p, "text") and p.text is not None:
                text = p.text
                entry.append({"kind": "text", "length": len(text) if isinstance(text, str) else 0})
            else:
                entry.append({"kind": "other"})
        parts_summaries.append(entry)
    out["candidates_parts_summary"] = parts_summaries
    return out


class AsyncClient:
    def __init__(self, client: genai.aio.Client):
        self.client = client

    @traceable(
        name="generate_image",
        run_type="tool",
        process_inputs=_process_inputs_generate_image,
        process_outputs=_process_outputs_generate_image,
    )
    async def generate_image(self, model: str, contents: list[str]):
        """
        使用指定的模型生成图片。
        contents 是 jpeg/jpg 文件 http url、或文本提示词；这个设计符合目前消息生图的需求。
        本方法已用 LangSmith @traceable 追踪输入与输出摘要。
        """
        parts = []
        for content in contents:
            # 如果是 jpeg url，则转换为 Part.from_uri
            if content.startswith("http") and (content.endswith(".jpeg") or content.endswith(".jpg")):
                parts.append(types.Part.from_uri(file_uri=content, mime_type="image/jpeg"))
            else:
                parts.append(types.Part.from_text(text=content))
        return await self.client.models.generate_content(
            model=model,
            contents=[
                types.Content(
                    role="user",
                    parts=parts,
                )
            ],
            config=GEN_CONTENT_CONFIG_IMAGE_9_16_1K_R_RATED_ROMANCE_DIRECTOR,
        )
