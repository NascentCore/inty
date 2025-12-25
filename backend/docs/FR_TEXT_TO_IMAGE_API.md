CREATED_BY_AGENT

## 目标

在后端代码库中新增一个**独立的**文生图封装层，用统一的接口包装：

- **Google Vertex AI Imagen**（通过 `google.genai`，模型名用 `google/` 前缀）
- **fal.ai Model APIs**（通过官方 `fal_client`）

注意：本封装**不接入**现有 Inty 的业务流程 / API 路由；后续由你在业务侧集成。

## 代码位置

- 统一封装入口：`app/external_services/text_to_image_api.py`
- fal.ai 适配层：`app/external_services/fal_ai.py`
- fal.ai 测试 fake：`app/external_services/fakes/fal_ai.py`

## 模型命名约定（重要）

- **Google Imagen**：必须使用 `google/<imagen-model-name>` 形式，例如：
  - `google/imagen-4.0-fast-generate-001`
  - `google/imagen-4.0-ultra-generate-001`
- **fal.ai**：直接使用 fal.ai 的 model id，例如：
  - `fal-ai/z-image/turbo`

兼容性：如果传入的模型名以 `imagen-` 开头但没有 `google/` 前缀，封装会按 Google 处理并打印 warning（便于逐步迁移）。

## 用法示例（Python）

### Google Vertex AI Imagen

```python
from app.external_services.text_to_image_api import (
    TextToImageGenerationRequest,
    generate_text_to_image,
)

result = generate_text_to_image(
    TextToImageGenerationRequest(
        model="google/imagen-4.0-fast-generate-001",
        prompt="A friendly companion smiling at the camera",
        num_images=2,
        provider_args={
            "aspect_ratio": "9:16",
            # 如果设置 output_gcs_uri，Imagen 会把结果写入 GCS，并在返回中给出 gs:// URI
            "output_gcs_uri": "gs://your-bucket/path-prefix",
            "output_mime_type": "image/jpeg",
        },
    )
)

for img in result.images:
    print(img.gcs_uri, img.public_url, img.rai_filtered_reason)
```

### fal.ai

```python
from app.external_services.text_to_image_api import (
    TextToImageGenerationRequest,
    generate_text_to_image,
)

result = generate_text_to_image(
    TextToImageGenerationRequest(
        model="fal-ai/z-image/turbo",
        prompt="A cute cat sitting on a sofa",
        num_images=2,
        seed=42,
        provider_args={
            # fal.ai 官方做法是设置环境变量 FAL_KEY；也可以通过 api_key 传入
            "api_key": "your-fal-key",
            "image_size": "landscape_4_3",
            "output_format": "png",
        },
    )
)

for img in result.images:
    print(img.url, img.width, img.height, img.mime_type)
```

## 依赖

- 已在根 `requirements.txt` 增加：`fal-client==0.10.0`

