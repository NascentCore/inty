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

from enum import StrEnum
from typing import List
from dataclasses import dataclass
import json
import os
from typing import Optional

import google.genai as genai
from google.genai import types
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import global_config_loaded_from_config_yaml


# Initialize Google Gen AI client with Vertex AI
# The client will use the same credentials as configured for GCS
client = None  # Will be initialized when needed


def get_genai_client():
    """Get or create Google Gen AI client with proper configuration"""
    global client
    if client is None:
        try:
            # Initialize with Vertex AI configuration
            # This will use the same service account credentials as GCS

            # Set environment variable for proper authentication
            credentials_path = global_config_loaded_from_config_yaml.gcs.credentials
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

            # Try to get project ID from credentials file
            project_id = None
            location = "us-central1"  # Default location for Imagen

            if os.path.exists(credentials_path):
                with open(credentials_path, "r") as f:
                    creds = json.load(f)
                    project_id = creds.get("project_id")

            if not project_id:
                # Fallback: try to get from environment or use default
                project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "inty-backend")

            # Clear any cached client to ensure fresh authentication
            if hasattr(genai, "_client_cache"):
                genai._client_cache.clear()

            client = genai.Client(vertexai=True, project=project_id, location=location)
            logger.info(
                f"Initialized Google Gen AI client with project: {project_id}, location: {location}"
            )
        except Exception as e:
            logger.error(f"Error initializing Google Gen AI client: {e}")
            # Fallback to basic initialization with environment variable set
            client = genai.Client(vertexai=True)

    return client


def enhance_prompt(prompt: str, gender: str) -> str:
    """
    增强提示词
    """
    # 获取反向性别

    # 构建增强提示词
    enhanced_prompt = f"""
    A person who is welcoming, friendly.
    age: 22 - 35
    gender: {gender}

    {prompt}

    Additional requirements:
    The image must be of a person.
    It cannot be a landscape, object, or any other non-human content.
    Avoid generating images of people appearing less than 18 years old.
    All content must be appropriate for a general audience.
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


def text_to_image(
    prompt: str,
    negative_prompt: str,
    enhanced_prompt: bool,
    gender: str,
    aspect_ratio: str,
    gcs_uri_base: str,
    count: int,
) -> List[ImagenGeneratedImage]:
    """
    使用output_gcs_uri参数直接将生成的背景图保存到GCS，返回实际生成的图片GCS路径列表
    支持includeRaiReason参数获取RAI过滤原因

    Args:
        prompt (str): 生成图片的描述提示词
        negative_prompt (str): 生成图片的负面提示词
        gcs_uri_base (str): GCS 存储基础URI
        count (int): 生成图片数量，默认为1
        aspect_ratio (str): 图片尺寸比例，默认为"9:16"

    Returns:
        list: 生成图片的HTTPS URL列表，或包含RAI原因的字典
    """
    try:
        logger.debug(
            f"Starting image generation with prompt: {prompt}, "
            f"negative_prompt: {negative_prompt}, "
            f"gcs_uri_base: {gcs_uri_base}, "
            f"count: {count}, "
            f"aspect_ratio: {aspect_ratio}"
        )

        # 使用新的Google Gen AI SDK生成图片
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
            model=global_config_loaded_from_config_yaml.agent.vertex_image_model,
            prompt=prompt,
            config=config,
        )

        logger.debug(f"Image generation response: {response}")

        generated_images = []
        # 处理每个生成的图片
        for i, image in enumerate(response.generated_images):
            # 获取GCS URI并转换为HTTPS URL
            gcs_uri = image.image.gcs_uri
            if gcs_uri.startswith("gs://"):
                gcs_path = gcs_uri[5:]  # 移除"gs://"前缀
                gcs_uri = f"https://storage.googleapis.com/{gcs_path}"
                logger.debug(f"Image {i}: {gcs_uri}")
            generated_images.append(
                ImagenGeneratedImage(
                    gcs_uri=gcs_uri,
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
