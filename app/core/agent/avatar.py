import google.genai as genai
from google.genai import types
import os
import json
from loguru import logger

from app.core.config import settings


# Initialize Google Gen AI client with Vertex AI
# The client will use the same credentials as configured for GCS
client = None  # Will be initialized when needed


def get_genai_client():
    """Get or create Google Gen AI client with proper configuration"""
    global client
    if client is None:
        try:
            # Import settings here to avoid circular import
            from app.core.config import settings

            # Initialize with Vertex AI configuration
            # This will use the same service account credentials as GCS

            # Try to get project ID from credentials file
            credentials_path = settings.gcs.credentials
            project_id = None
            location = "us-central1"  # Default location for Imagen

            if os.path.exists(credentials_path):
                with open(credentials_path, "r") as f:
                    creds = json.load(f)
                    project_id = creds.get("project_id")

            if not project_id:
                # Fallback: try to get from environment or use default
                project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "inty-backend")

            # TODO: 这里依赖本地缓存的身份信息，当运行于 Google Cloud 内部环境时，不需要额外控制
            # 即可运行；比如运行在同属于同样 project 的 VM 上时，不需要额外配置即可链接对应的 API。
            client = genai.Client(vertexai=True, project=project_id, location=location)
            logger.info(
                f"Initialized Google Gen AI client with project: {project_id}, location: {location}"
            )
        except Exception as e:
            logger.error(f"Error initializing Google Gen AI client: {e}")
            # Fallback to basic initialization
            client = genai.Client(vertexai=True)

    return client


def get_opposite_gender(user_gender: str) -> str:
    """
    获取用户性别的相反性别
    用于生成与用户性别相反的图片
    """
    if not user_gender:
        return ""

    gender_mapping = {
        "male": "female",
        "female": "male",
        "non-binary": "",
        "they/them": "",
        "nb": "",  # non-binary 的简写
        "other": "",
    }

    # 转换为小写进行匹配
    normalized_gender = user_gender.lower().strip()
    opposite = gender_mapping.get(normalized_gender, "")

    logger.info(
        f"User gender: {user_gender} -> Opposite gender for prompt: '{opposite}'"
    )
    return opposite


def generate_background_image_to_gcs(
    prompt: str,
    gcs_uri_base: str,
    count=1,
    aspect_ratio="9:16",
    gender: str = None,
    include_rai_reason=False,
):
    """
    使用output_gcs_uri参数直接将生成的背景图保存到GCS，返回实际生成的图片GCS路径列表
    支持includeRaiReason参数获取RAI过滤原因

    Args:
        prompt (str): 生成图片的描述提示词
        gcs_uri_base (str): GCS 存储基础URI
        count (int): 生成图片数量，默认为1
        aspect_ratio (str): 图片尺寸比例，默认为"9:16"
        gender (str): 用户性别，支持 "male", "female", "non-binary", "they/them" 等
        include_rai_reason (bool): 是否包含RAI过滤原因

    Returns:
        list: 生成图片的HTTPS URL列表，或包含RAI原因的字典
    """
    try:
        logger.info(f"Starting image generation with prompt: {prompt}, count: {count}")
        logger.info(f"Target GCS URI base: {gcs_uri_base}")
        logger.info(f"User gender: {gender}")

        # 获取反向性别
        opposite_gender = get_opposite_gender(gender)

        # 构建增强提示词
        enhanced_prompt = f"""
        A person who is welcoming, friendly.

        The person's description:
        {prompt}

        The person's information:
        age: 22 - 35
        gender: {opposite_gender}

        Additional requirements:
        The image must be of a person.
        It cannot be a landscape, object, or any other non-human content.
        Avoid generating images of people appearing less than 18 years old.
        All content must be appropriate for a general audience.
        """

        # 使用新的Google Gen AI SDK生成图片
        config = types.GenerateImagesConfig(
            number_of_images=count,
            aspect_ratio=aspect_ratio,
            # TODO: 上架期间仅生成低风险图片，选择屏蔽低风险和以上风险图片。
            safety_filter_level=types.SafetyFilterLevel.BLOCK_LOW_AND_ABOVE,
            person_generation=types.PersonGeneration.ALLOW_ADULT,
            output_gcs_uri=gcs_uri_base,
            include_rai_reason=include_rai_reason,
        )

        client = get_genai_client()
        response = client.models.generate_images(
            model=settings.agent.models.image_gen,
            prompt=enhanced_prompt,
            config=config,
        )

        # 处理响应中的图片
        generated_uris = []
        rai_reasons = []

        logger.info(f"Generated {len(response.generated_images)} images")

        # 处理每个生成的图片
        for i, image in enumerate(response.generated_images):
            # 检查是否被RAI过滤
            if image.rai_filtered_reason:
                rai_reasons.append(image.rai_filtered_reason)
                logger.warning(
                    f"Image {i} filtered by RAI: {image.rai_filtered_reason}"
                )
                continue

            # 获取GCS URI并转换为HTTPS URL
            gcs_uri = image.image.gcs_uri
            if gcs_uri:
                if gcs_uri.startswith("gs://"):
                    gcs_path = gcs_uri[5:]  # 移除"gs://"前缀
                    https_url = f"https://storage.googleapis.com/{gcs_path}"
                    generated_uris.append(https_url)
                    logger.info(f"Image {i}: {gcs_uri} -> {https_url}")
                else:
                    generated_uris.append(gcs_uri)
                    logger.info(f"Image {i}: {gcs_uri}")

        # 检查是否生成了任何图片
        if not generated_uris:
            error_msg = "No images were successfully generated. Please check whether the prompt contains any prohibited content"
            if rai_reasons:
                error_msg += f". RAI filtering reasons: {'; '.join(rai_reasons)}"
            raise Exception(error_msg)

        logger.info(f"Successfully generated {len(generated_uris)} images")

        # 根据include_rai_reason参数返回不同格式
        if include_rai_reason:
            return {"image_uris": generated_uris, "rai_reasons": rai_reasons}
        else:
            return generated_uris

    except Exception as e:
        logger.error(f"Error in generate_background_image_to_gcs: {e}")
        import traceback

        traceback.print_exc()
        raise e


if __name__ == "__main__":
    prompt = """
    The person's description:
    a beautiful girl

    The person's information:
    age: 22 - 35
    gender: female

    Important requirement: The image must be of a person. It cannot be a landscape, object, or any other non-human content.
    """

    # 使用新的SDK进行测试
    config = types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio="1:1",
        safety_filter_level=types.SafetyFilterLevel.BLOCK_MEDIUM_AND_ABOVE,
        person_generation=types.PersonGeneration.ALLOW_ADULT,
        include_rai_reason=True,
    )

    client = get_genai_client()
    response = client.models.generate_images(
        model="imagen-4.0-fast-generate-preview-06-06", prompt=prompt, config=config
    )

    for image in response.generated_images:
        if image.rai_filtered_reason:
            print(image.rai_filtered_reason)
        else:
            image.image.save("test.png")
