from loguru import logger
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from app.core.config import settings
from app.utils.gcs import upload_to_gcs
import uuid
import os
from datetime import datetime

# Initialize Vertex AI
vertexai.init()  # 使用你的Google Cloud项目ID

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
        "other": ""
    }
    
    # 转换为小写进行匹配
    normalized_gender = user_gender.lower().strip()
    opposite = gender_mapping.get(normalized_gender, "")
    
    print(f"User gender: {user_gender} -> Opposite gender for prompt: '{opposite}'")
    return opposite

def generate_background_image_to_gcs(prompt: str, gcs_uri_base: str, count=1, aspect_ratio="9:16", gender: str = None):
    """
    使用output_gcs_uri参数直接将生成的背景图保存到GCS，返回实际生成的图片GCS路径列表
    
    Args:
        prompt (str): 生成图片的描述提示词
        gcs_uri_base (str): GCS 存储基础URI
        count (int): 生成图片数量，默认为1
        aspect_ratio (str): 图片尺寸比例，默认为"9:16"
        gender (str): 用户性别，支持 "male", "female", "non-binary", "they/them" 等
    
    Returns:
        list: 生成图片的HTTPS URL列表
    """
    try:
        logger.info(f"Starting image generation with prompt: {prompt}, count: {count}")
        logger.info(f"Target GCS URI base: {gcs_uri_base}")
        logger.info(f"User gender: {gender}")
        
        model = ImageGenerationModel.from_pretrained("imagen-4.0-fast-generate-preview-06-06")
        
        # 获取反向性别
        opposite_gender = get_opposite_gender(gender)
        
        # 构建增强提示词
        enhanced_prompt = f"""
        The person's description:
        {prompt}
        
        The person's information:
        age: 22 - 35
        gender: {opposite_gender}
        """
        
        # 使用output_gcs_uri直接上传到GCS
        images = model.generate_images(
            prompt=enhanced_prompt,
            number_of_images=count,
            aspect_ratio=aspect_ratio,
            safety_filter_level="block_some",
            person_generation="allow_adult",
            output_gcs_uri=gcs_uri_base
        )
        
        print(f"Generated images type: {type(images)}")
        print(f"Images object attributes: {[attr for attr in dir(images) if not attr.startswith('__')]}")
        
        generated_uris = []
        
        # 直接通过images.images获取图片列表
        for i, image in enumerate(images.images):
            try:
                # 直接获取_gcs_uri属性
                gcs_uri = image._gcs_uri
                
                # 转换为HTTPS URL
                if gcs_uri.startswith("gs://"):
                    gcs_path = gcs_uri[5:]  # 移除"gs://"前缀
                    https_url = f"https://storage.googleapis.com/{gcs_path}"
                    generated_uris.append(https_url)
                    print(f"Image {i}: {gcs_uri} -> {https_url}")
                else:
                    generated_uris.append(gcs_uri)
                    print(f"Image {i}: {gcs_uri}")
                    
            except Exception as e:
                print(f"Error processing image {i}: {e}")
                continue
        
        if not generated_uris:
            raise Exception("No images were successfully generated，Please check whether the prompt contains any prohibited content")
        
        print(f"Successfully generated {len(generated_uris)} images")
        return generated_uris
        
    except Exception as e:
        print(f"Error in generate_background_image_to_gcs: {e}")
        import traceback
        traceback.print_exc()
        raise e


if __name__ == "__main__":

    prompt = "生成一个小女孩"

    model = ImageGenerationModel.from_pretrained("imagen-4.0-fast-generate-preview-06-06")
    images = model.generate_images(
        prompt=prompt,
        number_of_images=1,
        aspect_ratio="1:1",
        safety_filter_level="block_some",
        person_generation="allow_adult",
        # output_gcs_uri="gs://inty-static/tmp/output-image.png"
    )

    images[0].save(location="./output-image.png", include_generation_parameters=False)

    # Optional. View the generated image in a notebook.
    # images[0].show()


    print(f"Created output image using {len(images[0]._image_bytes)} bytes")
    # Example response:
    # Created output image using 1234567 bytes