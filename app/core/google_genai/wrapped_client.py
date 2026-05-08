"""Limitations of the official LangSmith tracing wrapper for the Google GenAI SDK.

Ref: https://docs.langchain.com/langsmith/trace-with-google-gemini#configure-tracing
Implementation: app.utils.google_genai_client.wrap_google_genai_client_with_langsmith
"""

from __future__ import annotations

import base64
import copy
import datetime
from enum import StrEnum
import io
import tempfile
import threading
from typing import Any, Literal
import uuid

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
# GenAI SDK 结束原因解释：https://ai.google.dev/api/generate-content#FinishReason


import PIL
from google import genai
from loguru import logger
from pydantic import BaseModel
from app.core.config import global_config_loaded_from_config_yaml
from app.core.google_genai.utils import (
    get_jpeg_url_and_text_mixed_parts,
    get_text_part,
    get_text_parts,
)
from google.genai import types as gemini_types
from langsmith.run_helpers import traceable

from app.core.google_genai.predefined_configs import (
    GEN_CONTENT_CONFIG_IMAGE_9_16_1K,
    GEN_CONTENT_CONFIG_IMAGE_9_16_1K_MLDEV,
)
from app.core.images.types import GeneratedImageProcessResult
from app.external_services.gcs import upload_to_gcs
from app.utils.gemini import get_genai_client, get_newapi_gemini_client
from app.utils.image import ImageFormat, ImageSize
from app.utils.langsmith import attach_provider_response_to_langsmith_run
from app.utils.models_catalog import NANO_BANANA, NANO_BANANA_PRO, NEWAPI_NANO_BANANA_2

# LangSmith trace 中只记录 raw_data 的前 N 字节，避免大块二进制写入 trace。
_LANGSMITH_RAW_DATA_TRACE_BYTES = 100
_LANGSMITH_OMITTED_RAW_IMAGE_DATA_TEXT = "[omitted raw image data after GCS upload]"


def _build_omitted_raw_image_data_marker(raw_value: Any) -> str:
    if isinstance(raw_value, bytes):
        return f"{_LANGSMITH_OMITTED_RAW_IMAGE_DATA_TEXT} ({len(raw_value)} bytes)"
    if isinstance(raw_value, str):
        return f"{_LANGSMITH_OMITTED_RAW_IMAGE_DATA_TEXT} ({len(raw_value)} chars)"
    return _LANGSMITH_OMITTED_RAW_IMAGE_DATA_TEXT


def _remove_raw_image_data_inplace(payload: dict[str, Any] | list[Any]) -> None:
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, (dict, list)):
                _remove_raw_image_data_inplace(item)
        return

    inline_data = payload.get("inline_data")
    if isinstance(inline_data, dict) and "data" in inline_data:
        inline_data["data"] = _build_omitted_raw_image_data_marker(inline_data["data"])

    for value in payload.values():
        if isinstance(value, (dict, list)):
            _remove_raw_image_data_inplace(value)


def _sanitize_provider_response_for_trace(response: Any) -> Any:
    """
    LangSmith trace 里不保留 provider raw response 内的图片原始数据，
    避免 trace 记录体积过大。
    """
    if response is None:
        return None

    if isinstance(response, dict):
        payload: Any = copy.deepcopy(response)
    elif isinstance(response, BaseModel):
        payload = response.model_dump(mode="python")
    else:
        model_dump = getattr(response, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump(mode="python")
            if isinstance(dumped, dict):
                payload = dumped
            else:
                return response
        else:
            return response

    if isinstance(payload, (dict, list)):
        _remove_raw_image_data_inplace(payload)
    return payload


class LangSmithTraceRunType(StrEnum):
    TOOL = "tool"
    CHAIN = "chain"
    LLM = "llm"
    RETRIEVER = "retriever"
    EMBEDDING = "embedding"
    PROMPT = "prompt"
    PARSER = "parser"


def _langsmith_process_outputs_generate_image(
    result: GeneratedImageProcessResult | None,
) -> GeneratedImageProcessResult | None:
    """
    process_outputs：供 LangSmith @traceable 使用，仅将 raw_data 的前 N 字节写入 trace，
    避免大块二进制数据；实际返回值不受影响。
    """
    if result is None:
        # 当有异常时，返回值为 None，需要处理，否则 LangSmith 记录会显示超时。
        return None
    raw_data = result.raw_data if isinstance(result.raw_data, bytes) else b""
    total = len(raw_data)
    truncated = raw_data[:_LANGSMITH_RAW_DATA_TRACE_BYTES]
    if result.gcs_uri:
        trace_raw_response = _sanitize_provider_response_for_trace(
            result.raw_response_from_provider
        )
    else:
        trace_raw_response = result.raw_response_from_provider
    return result.model_copy(
        update={
            "raw_data_total_bytes": total,
            "raw_data": base64.b64encode(truncated).decode("ascii"),
            "raw_response_from_provider": trace_raw_response,
        }
    )


def _langsmith_process_outputs_generate_images(
    results: list[GeneratedImageProcessResult] | None,
) -> list[GeneratedImageProcessResult] | None:
    """
    process_outputs for async_generate_images: delegates to _langsmith_process_outputs_generate_image
    per item so LangSmith trace receives a list of sanitized results (truncated raw_data).
    """
    if results is None:
        return None
    return [_langsmith_process_outputs_generate_image(r) for r in results]


class WrappedClient:
    def __init__(self, client: genai.Client):
        self.client = client

    @traceable(
        name="generate_image_with_google_genai",
        # LLM 是语言模型，生图模型就作为工具调用类型
        run_type=LangSmithTraceRunType.TOOL,
        # process_inputs=_process_inputs_generate_image,
        process_outputs=_langsmith_process_outputs_generate_images,
    )
    async def async_generate_images(
        self,
        model: Literal[
            NANO_BANANA.id_on_provider,
            NANO_BANANA_PRO.id_on_provider,
            NEWAPI_NANO_BANANA_2.id_on_provider,
        ],
        contents: list[str],
        gcs_uri_base: str,
        system_instructions: list[str] | None = None,
        count: int = 1,
    ) -> list[GeneratedImageProcessResult]:
        """
        使用指定的模型生成图片。
        contents 是 jpeg/jpg 文件 http url、或文本提示词；这个设计符合目前消息生图的需求。
        本方法已用 LangSmith @traceable 追踪输入与输出摘要。

        Parameters:
            model: 模型 ID，用于在代码中唯一标识一个模型。
            system_instructions: 系统指令列表。
            contents: 提示词列表，用于生成图片。
            count: 请求的候选数量（对应 Gemini candidate_count），默认 1。

        为了 traceable 可以争取抓取主要信息，必须把对结果有影响的参数暴露在这个函数的
        输入参数列表内，这是 LangSmith 的要求。LangSmith 无法抓取 GenAI.generate_contents() 参数。

        参数要简单，不能太复杂，否则 LangSmith 无法抓取主要信息。

        Returns:
            list[GeneratedImageProcessResult]（每项含 size, format, raw_data, gcs_uri, generated_at）。
            当前仅支持 Gemini（NANO_BANANA*）路径；Imagen 模型会抛出 ValueError。
        """
        match model:
            case (
                NANO_BANANA.id_on_provider
                | NANO_BANANA_PRO.id_on_provider
                | NEWAPI_NANO_BANANA_2.id_on_provider
            ):
                # 新的多模态模型 API 使用 generate_content 方法，支持文本和图像输入。
                # 复制 config 以设置 candidate_count 及可选的 system_instruction，避免污染全局预设。
                use_newapi = model == NEWAPI_NANO_BANANA_2.id_on_provider
                newapi_client = get_newapi_gemini_client() if use_newapi else None
                if use_newapi and newapi_client is None:
                    raise ValueError(
                        "消息生图模型为 NewAPI Nano Banana 2 时需在配置中设置 "
                        "agent.newapi_gemini_base_url 与 Bearer（或 NEWAPI_GEMINI_BEARER_TOKEN）"
                    )
                gen_client = newapi_client or self.client
                base_cfg = (
                    GEN_CONTENT_CONFIG_IMAGE_9_16_1K_MLDEV
                    if newapi_client
                    else GEN_CONTENT_CONFIG_IMAGE_9_16_1K
                )
                config = copy.copy(base_cfg)
                config.candidate_count = count
                if system_instructions is not None:
                    config.system_instruction = get_text_parts(system_instructions)

                contents_parts = get_jpeg_url_and_text_mixed_parts(contents)
                response = await gen_client.aio.models.generate_content(
                    model=model,
                    contents=[
                        gemini_types.Content(
                            role="user",
                            parts=contents_parts,
                        )
                    ],
                    config=config,
                )
                trace_response = _sanitize_provider_response_for_trace(response)
                attach_provider_response_to_langsmith_run(trace_response)
                _validate_gemini_image_response(response)
                parts = []
                for candidate in response.candidates:
                    parts.append(_process_one_candidate(candidate))
                results = []
                for part in parts:
                    result = _process_image_part_to_generated_image(part, gcs_uri_base)
                    result.raw_response_from_provider = response
                    results.append(result)
                return results

            case _:
                raise ValueError(f"Unsupported model: {model}")


def _validate_gemini_image_response(response: Any) -> None:
    """
    校验 Gemini generate_content 响应级别的反馈与候选数量。
    若 prompt 被安全策略阻止或没有候选，记录日志并抛出 ValueError。
    """
    if hasattr(response, "prompt_feedback") and response.prompt_feedback:
        prompt_feedback = response.prompt_feedback
        logger.warning("Prompt feedback: {}", prompt_feedback)
        if hasattr(prompt_feedback, "block_reason") and prompt_feedback.block_reason:
            logger.warning("请求被阻止，原因: {}", prompt_feedback.block_reason)
            raise ValueError(
                f"Image generation request blocked by safety filter: {prompt_feedback.block_reason}"
            )

    if not response.candidates:
        logger.error("Gemini 未返回任何候选结果")
        raise ValueError("Gemini returned no candidates")


def _format_safety_rating(r: Any) -> str:
    """Single safety rating line for logging/error messages."""
    return f"{r.category}={r.probability}(blocked={r.blocked})"


def _process_one_candidate(candidate: Any) -> gemini_types.Part:
    """
    校验单个 Gemini 候选结果并提取图片 part。
    成功时返回含有 inline_data 的 part；失败时记录日志并抛出 ValueError。
    """
    # 检查 finish_reason（完成原因）
    finish_reason = getattr(candidate, "finish_reason", None)
    finish_reason_text = str(finish_reason) if finish_reason is not None else ""
    normalized_finish_reason = (
        finish_reason_text.split(".")[-1].upper() if finish_reason_text else ""
    )
    if finish_reason:
        logger.warning("候选结果完成原因: {}", finish_reason)
        if normalized_finish_reason in {
            "SAFETY",
            "IMAGE_SAFETY",
            "IMAGE_PROHIBITED_CONTENT",
        }:
            safety_ratings = getattr(candidate, "safety_ratings", None) or []
            safety_details = [_format_safety_rating(r) for r in safety_ratings]
            error_msg = (
                "Image generation blocked by safety filter "
                f"(finish_reason: {finish_reason_text})"
            )
            if safety_details:
                error_msg += f"; details: {', '.join(safety_details)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        elif normalized_finish_reason not in {"STOP", ""}:
            logger.warning("候选结果以非正常原因结束: {}", finish_reason)

    # 检查 safety_ratings（即使 finish_reason 不是 SAFETY，也可能有安全评级）
    candidate_safety_ratings = getattr(candidate, "safety_ratings", None) or []
    blocked_ratings = [
        _format_safety_rating(r)
        for r in candidate_safety_ratings
        if hasattr(r, "blocked") and r.blocked
    ]
    if blocked_ratings:
        error_msg = (
            f"Image generation blocked by safety filter: {', '.join(blocked_ratings)}"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    # 检查 content 和 parts
    if not candidate.content or not candidate.content.parts:
        logger.error("候选结果中没有内容，finish_reason={}", finish_reason)
        error_msg = "No content in candidates"
        if finish_reason:
            error_msg += f" (finish_reason: {finish_reason})"
        raise ValueError(error_msg)

    # 查找图片部分
    image_part = None
    for part in candidate.content.parts:
        if hasattr(part, "inline_data") and part.inline_data:
            image_part = part
            break

    if not image_part:
        raise ValueError("No image data found in response")

    return image_part


def _extract_image_part_from_gemini_response(
    response: gemini_types.GeneratedContent,
) -> gemini_types.Part:
    """
    校验 Gemini generate_content 响应并提取图片 part。
    成功时返回含有 inline_data 的 part；失败时记录日志并抛出 ValueError。
    """
    _validate_gemini_image_response(response)
    return _process_one_candidate(response.candidates[0])


def _process_image_part_to_generated_image(
    image_part: gemini_types.Part,
    gcs_uri_base: str,
) -> GeneratedImageProcessResult:
    """
    从 Gemini 返回的 image_part（inline_data）解析图片、上传 GCS，返回 generated_image 元数据及 image_data、gcs_uri。
    """
    logger.debug("inline_data 类型: {}", type(image_part.inline_data))
    logger.debug("inline_data.data 类型: {}", type(image_part.inline_data.data))
    if hasattr(image_part.inline_data, "mime_type"):
        logger.debug(
            "inline_data.mime_type: {}",
            image_part.inline_data.mime_type,
        )

    raw_data = image_part.inline_data.data
    if isinstance(raw_data, str):
        image_data = base64.b64decode(raw_data)
        logger.debug("数据是 base64 字符串，已解码")
    elif isinstance(raw_data, bytes):
        image_data = raw_data
        logger.debug("数据已经是 bytes，直接使用")
    else:
        logger.error("未知的数据类型: {}", type(raw_data))
        raise ValueError(f"Unsupported image data type: {type(raw_data)}")

    logger.info("成功提取图片数据，大小: {} bytes", len(image_data))
    if len(image_data) == 0:
        raise ValueError("Image data is empty")

    header = image_data[:20] if len(image_data) >= 20 else image_data
    logger.debug("图片数据头部（hex）: {}", header.hex())

    if image_data[:2] == b"\xff\xd8":
        logger.debug("检测到 JPEG 格式")
    elif image_data[:8] == b"\x89PNG\r\n\x1a\n":
        logger.debug("检测到 PNG 格式")
    elif image_data[:6] in (b"GIF87a", b"GIF89a"):
        logger.debug("检测到 GIF 格式")
    elif image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP":
        logger.debug("检测到 WEBP 格式")
    else:
        logger.warning("未知的图片格式，尝试作为原始数据处理")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
            tmp.write(image_data)
            logger.debug("原始数据已写入: {}", tmp.name)

    try:
        pil_image = PIL.Image.open(io.BytesIO(image_data))
        width, height = pil_image.size
        image_format = pil_image.format
        logger.info("成功解析图片: {}x{}, 格式: {}", width, height, image_format)
    except Exception as e:
        logger.error("PIL 无法解析图片: {}", str(e))
        try:
            text_content = image_data.decode("utf-8")[:200]
            logger.error("数据可能是文本: {}", text_content)
        except (UnicodeDecodeError, ValueError, AttributeError):
            # 仅避免 decode 失败掩盖主异常，不改变主流程
            pass
        raise ValueError(f"Unable to parse image data: {e}") from e

    # 按实际格式设置 content_type 与扩展名，避免将 PNG 等误标为 JPEG
    _FORMAT_TO_MIME = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "GIF": "image/gif",
        "WEBP": "image/webp",
    }
    _FORMAT_TO_EXT = {"JPEG": "jpg", "PNG": "png", "GIF": "gif", "WEBP": "webp"}
    fmt_upper = (image_format or "JPEG").upper()
    content_type = _FORMAT_TO_MIME.get(fmt_upper, "image/jpeg")
    ext = _FORMAT_TO_EXT.get(fmt_upper, "jpg")

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    gcs_path = f"{gcs_uri_base}/{timestamp}_{uuid.uuid4().hex[:8]}.{ext}"
    bucket_name = global_config_loaded_from_config_yaml.gcs.bucket
    gcs_http_url = upload_to_gcs(
        file_data=image_data,
        content_type=content_type,
        bucket_name=bucket_name,
        path=gcs_path,
    )
    gcs_uri = f"gs://{bucket_name}/{gcs_path}"
    logger.info("图片已上传到 GCS: {}", gcs_uri)

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    return GeneratedImageProcessResult(
        size=ImageSize(width=width, height=height),
        format=ImageFormat(image_format.lower()),
        raw_data=image_data,
        gcs_uri=gcs_uri,
        gcs_http_url=gcs_http_url,
        generated_at=now_utc,
    )


_wrapped_client = None
_wrapped_client_lock = threading.Lock()


def get_wrapped_client() -> WrappedClient:
    """
    获取 wrapped client。
    """
    global _wrapped_client
    with _wrapped_client_lock:
        if _wrapped_client is None:
            base_client = get_genai_client()
            _wrapped_client = WrappedClient(client=base_client)
    return _wrapped_client
