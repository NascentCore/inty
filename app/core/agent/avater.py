import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

# TODO(developer): Update and un-comment below lines
# PROJECT_ID = "your-project-id"
# output_file = "input-image.png"
# prompt = "" # The text prompt describing what you want to see.

vertexai.init()

def generate_background_image_to_gcs(prompt: str, gcs_uri: str, aspect_ratio="16:9"):
    """
    直接将生成的背景图保存到GCS，返回实际生成的图片GCS路径
    注意：Vertex AI Imagen模型会在指定的基础路径后自动添加时间戳目录和实际文件名
    """
    model = ImageGenerationModel.from_pretrained("imagen-4.0-fast-generate-preview-06-06")
    images = model.generate_images(
        prompt=prompt,
        number_of_images=1,
        aspect_ratio=aspect_ratio,
        safety_filter_level="block_some",
        person_generation="allow_all",
        output_gcs_uri=gcs_uri
    )
    
    # 获取实际生成的图片GCS路径
    # Vertex AI会在提供的基础路径后添加时间戳和文件名
    if images:
        # ImageGenerationResponse对象不支持len()，直接访问images属性
        if hasattr(images, 'images') and images.images:
            image = images.images[0]
        else:
            # 如果images对象本身就是图片列表
            image = images[0] if hasattr(images, '__getitem__') else images
        
        # 方法1: 检查gcs_uri属性
        if hasattr(image, 'gcs_uri') and image.gcs_uri:
            return image.gcs_uri
        
        # 方法2: 检查_gcs_uri属性
        if hasattr(image, '_gcs_uri') and image._gcs_uri:
            return image._gcs_uri
            
        # 方法3: 检查是否有storage_uri属性
        if hasattr(image, 'storage_uri') and image.storage_uri:
            return image.storage_uri
            
        # 方法4: 尝试从image对象的其他属性获取
        # 打印可用属性以便调试
        print(f"Available attributes: {[attr for attr in dir(image) if not attr.startswith('__')]}")
        
        # 如果所有方法都失败，检查是否有其他包含'uri'的属性
        for attr in dir(image):
            if 'uri' in attr.lower() and not attr.startswith('_'):
                uri_value = getattr(image, attr, None)
                if uri_value and isinstance(uri_value, str) and uri_value.startswith('gs://'):
                    return uri_value
    
    # 如果无法获取实际路径，返回原始路径（作为备用）
    print(f"Warning: Could not get actual GCS URI, returning base path: {gcs_uri}")
    return gcs_uri


if __name__ == "__main__":

    prompt = "生成孔子的头像"

    model = ImageGenerationModel.from_pretrained("imagen-4.0-fast-generate-preview-06-06")
    images = model.generate_images(
        prompt=prompt,
        number_of_images=1,
        aspect_ratio="1:1",
        safety_filter_level="block_some",
        person_generation="allow_adult",
        output_gcs_uri="gs://inty-static/tmp/output-image.png"
    )

    images[0].save(location="./output-image.png", include_generation_parameters=False)

    # Optional. View the generated image in a notebook.
    # images[0].show()

    print(f"Created output image using {len(images[0]._image_bytes)} bytes")
    # Example response:
    # Created output image using 1234567 bytes