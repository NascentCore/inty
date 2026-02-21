"""Limitations of the official LangSmith tracing wrapper for the Google GenAI SDK.

Ref: https://docs.langchain.com/langsmith/trace-with-google-gemini#configure-tracing
Implementation: app.utils.google_genai_client.wrap_google_genai_client_with_langsmith
"""
from __future__ import annotations
from enum import StrEnum
from typing import Literal

# -----------------------------------------------------------------------------
# Official wrapper: langsmith.wrappers.wrap_gemini
# -----------------------------------------------------------------------------
#
# 1. Only generate_content and generate_content_stream are traced
#    - client.models.generate_images (Imagen) is NOT wrapped.
#    - Imagen calls produce no LangSmith run; "full model request" is unavailable
#      unless you add your own @traceable or span around generate_images.
#
# Imagen generate_images API notes:
#    - Built-in GCS upload: pass output_gcs_uri in GenerateImagesConfig; the SDK
#      writes generated images to that URI (no app-side upload).
#    - Compression/quality: GenerateImagesConfig supports output_compression_quality
#      (int 0-100) for JPEG; optional, not set in our Imagen 4 branch below.
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

from app.core.google_genai.predefined_configs import ASPECT_RATIO_9_16, GEN_CONTENT_CONFIG_IMAGE_9_16_1K_R_RATED_ROMANCE_DIRECTOR
from app.utils.models_catalog import IMAGEN_4, IMAGEN_4_FAST, NANO_BANANA, NANO_BANANA_PRO


class LangSmithTraceRunType(StrEnum):
    TOOL = "tool"
    CHAIN = "chain"
    LLM = "llm"
    RETRIEVER = "retriever"
    EMBEDDING = "embedding"
    PROMPT = "prompt"
    PARSER = "parser"


class WrappedClient:
    def __init__(self, client: genai.Client):
        self.client = client

    @traceable(
        name="generate_image",
        run_type=LangSmithTraceRunType.LLM,
        # process_inputs=_process_inputs_generate_image,
        # process_outputs=_process_outputs_generate_image,
    )
    async def async_generate_image(
        self, 
        model: Literal[
            NANO_BANANA.id_on_provider,
            NANO_BANANA_PRO.id_on_provider,
            IMAGEN_4_FAST.id_on_provider,
            IMAGEN_4.id_on_provider,
        ],
        contents: list[str]) -> types.GeneratedContent:
        """
        使用指定的模型生成图片。
        contents 是 jpeg/jpg 文件 http url、或文本提示词；这个设计符合目前消息生图的需求。
        本方法已用 LangSmith @traceable 追踪输入与输出摘要。

        Parameters:
            model: 模型 ID，用于在代码中唯一标识一个模型。
            contents: 提示词列表，用于生成图片。

        Returns:
            types.GeneratedContent 对象，包含生成的图片。
        """
        match model:
            case NANO_BANANA.id_on_provider | NANO_BANANA_PRO.id_on_provider:
                # 新的多模态模型 API 使用 generate_content 方法，支持文本和图像输入。
                parts = []
                for content in contents:
                    # 如果是 jpeg url，则转换为 Part.from_uri
                    if content.startswith("http") and (content.endswith(".jpeg") or content.endswith(".jpg")):
                        parts.append(types.Part.from_uri(file_uri=content, mime_type="image/jpeg"))
                    else:
                        parts.append(types.Part.from_text(text=content))
                return await self.client.aio.models.generate_content(
                    model=model,
                    contents=[
                        types.Content(
                            role="user",
                            parts=parts,
                        )
                    ],
                    config=GEN_CONTENT_CONFIG_IMAGE_9_16_1K_R_RATED_ROMANCE_DIRECTOR,
                )
            case IMAGEN_4_FAST.id_on_provider | IMAGEN_4.id_on_provider:
                if len(contents) != 1:
                    raise ValueError("Imagen 4.0 Fast 和 Imagen 4.0 模型只支持一个提示词")
                # Imagen generate_images: no output_gcs_uri here (caller handles storage).
                # Optional: output_compression_quality (0-100) for JPEG.
                return await self.client.aio.models.generate_images(
                    model=model,
                    prompt=contents[0],
                    # TODO: 需要替换为现有代码中实际使用的 API 配置
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio=ASPECT_RATIO_9_16,
                    ),
                )
            case _:
                raise ValueError(f"Unsupported model: {model}")
