"""
Wrappers of Gemini API. There are 2 sets of APIs:

* google.genai, which is called Gemini API here: https://github.com/googleapis/python-genai
* Vertex AI API: https://github.com/googleapis/python-aiplatform

They share the same billing system provided by Google Cloud.

They differ in:

* They offer different sets of models, for example genai by Gemini offers imagen 4.
* Vertex AI SDK wraps google.genai, which provides direct integration with Google Cloud platform.
  For example, login through Google Cloud credentials.

This file is for the genai API.
"""

import contextlib
import io
import json
import os
from enum import StrEnum
import threading
from collections.abc import Iterator
from typing import List, Optional

from google import genai
import PIL
from google.genai import types
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import global_config_loaded_from_config_yaml
from app.core.agentic_kernel.providers.gemini import (
    GeminiClientOptions,
    get_gemini_client as get_kernel_gemini_client,
)
from app.external_services.fakes.gemini import FakeGeminiClient
from app.external_services.gcs import (
    delete_from_gcs,
    download_from_gcs,
    get_bucket_and_path_from_gcs_url,
    upload_to_gcs,
)
from app.utils.image import (
    ImageFormat,
    ImageSize,
    crop_image_to_9_16,
    get_jpg_bytes_from_pil_image,
)

# Initialize Google Gen AI client with Vertex AI
# The client will use the same credentials as configured for GCS
_google_genai_client = None  # Will be initialized when needed
_google_genai_client_lock = threading.Lock()


def create_google_genai_client():
    """
    使用 Vertex AI 配置创建并返回包装后的 Google Gen AI 客户端。
    使用与 GCS 相同的 service account 凭证；可抛出 ValueError 或 genai 相关异常。
    """
    credentials_path = global_config_loaded_from_config_yaml.app.gcp_service_account_key
    if not os.path.exists(credentials_path):
        raise ValueError(
            f"Service account credentials file not found at: {credentials_path}"
        )

    location = global_config_loaded_from_config_yaml.agent.vertex_ai_location
    project_id = None
    if os.path.exists(credentials_path):
        with open(credentials_path, "r") as f:
            creds = json.load(f)
            project_id = creds.get("project_id")

    if not project_id:
        raise ValueError(
            f"Project ID not found in credentials file: {credentials_path}"
        )

    if hasattr(genai, "_client_cache"):
        genai._client_cache.clear()

    return get_kernel_gemini_client(
        GeminiClientOptions(
            vertexai=True,
            project=project_id,
            location=location,
            credentials_path=credentials_path,
            wrap_langsmith=False,
        )
    )


def get_genai_client():
    """
    获取或创建 Google Gen AI 客户端。
    """
    global _google_genai_client
    with _google_genai_client_lock:
        if _google_genai_client is None:
            from app.core.config import Environment

            if (
                global_config_loaded_from_config_yaml.app.environment
                == Environment.TEST
            ):
                logger.info("Using FakeGeminiClient in test environment")
                _google_genai_client = FakeGeminiClient()
            else:
                logger.info("Creating Google Gen AI client")
                _google_genai_client = create_google_genai_client()
    return _google_genai_client


_GOOGLE_ENV_POP = (
    "GOOGLE_CLOUD_LOCATION",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
)
_newapi_client_cache: tuple[str, str, genai.Client] | None = None
_newapi_client_lock = threading.Lock()


@contextlib.contextmanager
def _without_google_env_for_newapi() -> Iterator[None]:
    saved = {k: os.environ[k] for k in _GOOGLE_ENV_POP if k in os.environ}
    try:
        for k in _GOOGLE_ENV_POP:
            os.environ.pop(k, None)
        yield
    finally:
        for k in _GOOGLE_ENV_POP:
            os.environ.pop(k, None)
        os.environ.update(saved)


def get_newapi_gemini_client() -> genai.Client | None:
    """若配置了 newapi_gemini_base_url 则返回指向 NewAPI 的 client，否则 None。"""
    global _newapi_client_cache
    agent = global_config_loaded_from_config_yaml.agent
    base = (agent.newapi_gemini_base_url or "").strip().rstrip("/")
    if not base:
        return None
    tok = (agent.newapi_gemini_bearer_token or "").strip() or (
        os.environ.get("NEWAPI_GEMINI_BEARER_TOKEN") or ""
    ).strip()
    key = (base, tok)
    with _newapi_client_lock:
        if _newapi_client_cache and _newapi_client_cache[0:2] == key:
            return _newapi_client_cache[2]
        hdrs = {"Authorization": f"Bearer {tok}"}
        with _without_google_env_for_newapi():
            client = genai.Client(
                vertexai=False,
                api_key=tok,
                http_options=types.HttpOptions(
                    base_url=base,
                    headers=hdrs,
                    api_version="v1beta",
                ),
            )
        _newapi_client_cache = (base, tok, client)
        return client


def enhance_prompt(prompt: str, gender: str) -> str:
    enhanced_prompt = f"""
    A person who is attractive/beautiful/lovely/intriguing.
    age: 22 - 35
    gender: {gender}

    {prompt}

    Additional requirements:
    - The image must be of a person at the center of the image.
      - Never put the person on the side
    - It cannot be a landscape, object, or any other non-human content.
    """

    logger.debug(f"Enhanced prompt: {enhanced_prompt}")
    return enhanced_prompt


class ImagenGeneratedImage(BaseModel):
    """
    An output image from Imagen API.
    This has keep the same as types.GeneratedImage from the google.genai package.
    It is used to wrap the types.GeneratedImage to make it more user-friendly.
    """

    gcs_uri: Optional[str] = Field(
        default=None,
        description="""The output image's GCS URI. None if filtered out by RAI.""",
    )
    size: Optional[ImageSize] = Field(
        default=None,
        description="""The size of the generated image.""",
    )
    byte_size: Optional[int] = Field(
        default=None,
        description="""The byte size of the generated image.""",
    )
    format: Optional[ImageFormat] = Field(
        default=None,
        description="""The format of the generated image.""",
    )
    rai_filtered_reason: Optional[str] = Field(
        default=None,
        description="""Reason why this image is filtered out. None if not filtered out.""",
    )
    enhanced_prompt: str = Field(
        ...,
        description="""The rewritten prompt used for the image generation.""",
    )


class MimeType(StrEnum):
    JPEG = "image/jpeg"


def generate_image_description(image_uri: str) -> str:
    """
    使用 Gemini Vision API 从图片生成描述

    Args:
        image_uri: 图片的 GCS URI（gs:// 格式）或 HTTPS URL

    Returns:
        图片的中文描述文本，适合作为视频生成提示词
    """
    try:
        logger.debug(f"开始生成图片描述，图片 URI: {image_uri}")

        client = get_genai_client()

        # 将 GCS URI 转换为 HTTPS URL（如果需要）
        # types.Part.from_uri() 可能支持 gs:// 格式，但为了兼容性，转换为 HTTPS
        if image_uri.startswith("gs://"):
            # 转换为 https://storage.googleapis.com/bucket/path 格式
            gcs_path = image_uri[5:]  # 移除 "gs://" 前缀
            image_uri = f"https://storage.googleapis.com/{gcs_path}"

        # 准备输入：图片 + 文本提示词
        image_part = types.Part.from_uri(
            file_uri=image_uri,
            mime_type="image/jpeg",  # 假设是 JPEG，实际可能是其他格式，但 API 通常会自动检测
        )

        prompt_text = """请用中文简洁地描述这张图片的内容，描述应该适合作为视频生成的提示词。
要求：
1. 描述图片中的主要人物、场景、动作和氛围
2. 使用简洁的中文，长度控制在50字以内
3. 描述应该能够指导视频生成，包含动态元素
4. 如果图片中有角色，描述角色的外观和动作
5. 如果图片是场景，描述场景的氛围和可能的动态效果

只返回描述文本，不要包含其他解释。"""

        contents = [
            types.Content(
                role="user",
                parts=[
                    image_part,
                    types.Part.from_text(text=prompt_text),
                ],
            )
        ]

        # 配置生成参数
        generate_config = types.GenerateContentConfig(
            temperature=0.7,
            top_p=0.95,
            max_output_tokens=200,
        )

        # 调用 Gemini 生成描述
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=generate_config,
        )

        # 检查 prompt_feedback
        if hasattr(response, "prompt_feedback") and response.prompt_feedback:
            prompt_feedback = response.prompt_feedback
            logger.warning(f"Prompt feedback: {prompt_feedback}")
            if hasattr(prompt_feedback, "block_reason"):
                block_reason = prompt_feedback.block_reason
                logger.warning(f"请求被阻止，原因: {block_reason}")
                raise ValueError(
                    f"Image description request blocked by safety filter: {block_reason}"
                )

        # 提取文本描述
        if not response.candidates or len(response.candidates) == 0:
            logger.error("Gemini 未返回任何候选结果")
            raise ValueError("Gemini returned no candidates")

        candidate = response.candidates[0]

        # 检查 finish_reason
        finish_reason = getattr(candidate, "finish_reason", None)
        if finish_reason and finish_reason != "STOP":
            logger.warning(f"候选结果完成原因: {finish_reason}")
            if finish_reason == "SAFETY":
                raise ValueError(
                    "Image description generation blocked by safety filter"
                )

        # 提取文本内容
        if not candidate.content or not candidate.content.parts:
            logger.error("候选结果中没有内容")
            raise ValueError("No content in candidates")

        description_text = ""
        for part in candidate.content.parts:
            if hasattr(part, "text") and part.text:
                description_text += part.text

        if not description_text:
            logger.error("无法从响应中提取文本描述")
            raise ValueError("Unable to extract text description from response")

        logger.info(f"图片描述生成成功: {description_text}")
        return description_text.strip()

    except Exception as e:
        logger.error(f"生成图片描述失败: {str(e)}")
        raise


def text_to_image(
    prompt: str,
    negative_prompt: str,
    enhanced_prompt: bool,
    gender: str,
    aspect_ratio: str,
    gcs_uri_base: str,
    count: int,
    model: Optional[str] = None,
) -> List[ImagenGeneratedImage]:
    """
    使用 output_gcs_uri 将生成的背景图由 SDK 直接写入 GCS，返回实际生成的图片
    GCS 路径列表。支持 include_rai_reason 获取 RAI 过滤原因。

    GCS：generate_images 在 config 中传入 output_gcs_uri 后由 SDK 直接上传，
    无需应用侧再调用 upload_to_gcs。可选：output_compression_quality (0-100)
    可控制 JPEG 压缩质量，当前未传。

    Args:
        prompt (str): 生成图片的描述提示词
        negative_prompt (str): 生成图片的负面提示词
        gcs_uri_base (str): GCS 存储基础 URI
        count (int): 生成图片数量，默认为1
        aspect_ratio (str): 图片尺寸比例，默认为"9:16"

    Returns:
        list: 生成图片的 GCS/HTTPS 信息列表，或包含 RAI 原因的字典
    """
    try:
        logger.debug(
            f"Starting image generation with prompt: {prompt}, "
            f"negative_prompt: {negative_prompt}, "
            f"gcs_uri_base: {gcs_uri_base}, "
            f"count: {count}, "
            f"aspect_ratio: {aspect_ratio}"
        )

        # 使用新的 Google Gen AI SDK 生成图片；SDK 按 output_gcs_uri 直接写入 GCS。
        # 可选 output_compression_quality (0-100) 未传，使用 SDK 默认。
        config = types.GenerateImagesConfig(
            negative_prompt=negative_prompt,
            number_of_images=count,
            aspect_ratio=aspect_ratio,
            # TODO: 上架期间仅生成低风险图片，选择屏蔽低风险和以上风险图片。
            safety_filter_level=types.SafetyFilterLevel.BLOCK_LOW_AND_ABOVE,
            person_generation=types.PersonGeneration.ALLOW_ADULT,
            output_gcs_uri=gcs_uri_base,
            include_rai_reason=True,
            # This reduces the size significantly.
            output_mime_type=MimeType.JPEG,
            # This is imagen's own enhancement, not the one from inty-backend's own enhancement.
            enhance_prompt=enhanced_prompt,
        )

        client = get_genai_client()
        if enhanced_prompt:
            prompt = enhance_prompt(prompt, gender)
        response = client.models.generate_images(
            # TODO: 这里的 fallback 逻辑是否需要？外层已经有多处 fallback，这里是否重复？
            model=model
            or global_config_loaded_from_config_yaml.agent.vertex_image_model,
            prompt=prompt,
            config=config,
        )

        logger.debug(f"Image generation response: {response}")

        generated_images = []
        # 处理每个生成的图片
        for i, image in enumerate(response.generated_images):
            # 获取GCS URI并转换为HTTPS URL
            gcs_uri = image.image.gcs_uri
            if gcs_uri and gcs_uri.startswith("gs://"):
                gcs_path = gcs_uri[5:]  # 移除"gs://"前缀
                gcs_uri = f"https://storage.googleapis.com/{gcs_path}"
                logger.debug(f"Image {i}: {gcs_uri}")
            elif gcs_uri is None:
                logger.debug(f"Image {i}: Filtered by RAI - no GCS URI available")

            # Try to get size from image.image.image_bytes if available
            size = None
            byte_size = 0
            if gcs_uri:
                # TODO: 考虑取消自动 gcs 上传，本地处理上传，这样就不用下载了。
                image_bytes = download_from_gcs(gcs_uri)
                byte_size = len(image_bytes)
                pil_image = PIL.Image.open(io.BytesIO(image_bytes))
                original_size = (pil_image.width, pil_image.height)

                # 检查并自动裁剪到 9:16 比例（生成背景图时自动裁剪）
                target_aspect_ratio = 9 / 16
                current_aspect_ratio = pil_image.width / pil_image.height

                if abs(current_aspect_ratio - target_aspect_ratio) >= 0.01:
                    # 需要裁剪
                    try:
                        logger.info(
                            f"图片 {i} 需要裁剪: {original_size[0]}x{original_size[1]} "
                            f"(比例 {current_aspect_ratio:.4f}) -> 9:16"
                        )
                        cropped_image = crop_image_to_9_16(pil_image)
                        cropped_size = (cropped_image.width, cropped_image.height)

                        # 将裁剪后的图片转换为 JPEG bytes
                        cropped_image_bytes = get_jpg_bytes_from_pil_image(
                            cropped_image, quality=95
                        )

                        # 从 GCS URI 提取 bucket 和 path
                        bucket_name, gcs_path = get_bucket_and_path_from_gcs_url(
                            gcs_uri
                        )

                        # 删除原图
                        delete_from_gcs(bucket_name, gcs_path)

                        # 上传裁剪后的图片到同一位置
                        upload_to_gcs(
                            cropped_image_bytes,
                            "image/jpeg",
                            bucket_name,
                            gcs_path,
                        )

                        # 更新尺寸和字节大小
                        pil_image = cropped_image
                        byte_size = len(cropped_image_bytes)
                        logger.info(
                            f"图片 {i} 裁剪完成: {original_size[0]}x{original_size[1]} -> "
                            f"{cropped_size[0]}x{cropped_size[1]}"
                        )
                    except Exception as crop_error:
                        logger.error(
                            f"裁剪图片 {i} 失败: {str(crop_error)}，使用原始图片"
                        )
                        # 裁剪失败时使用原始图片，不影响主流程

                size = ImageSize(
                    width=pil_image.width,
                    height=pil_image.height,
                )

            generated_images.append(
                ImagenGeneratedImage(
                    gcs_uri=gcs_uri,
                    size=size,
                    byte_size=byte_size,
                    format=ImageFormat.JPEG,
                    rai_filtered_reason=image.rai_filtered_reason,
                    enhanced_prompt=image.enhanced_prompt or "",
                )
            )
        return generated_images
    except Exception as e:
        logger.error(f"Error in generate_background_image_to_gcs: {e}")
        import traceback

        traceback.print_exc()
        raise e
