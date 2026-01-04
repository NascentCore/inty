# fal.ai 图片生成集成情况总结

## 概述

`app/` 目录中已实现 fal.ai 图片生成的基础集成，但**尚未接入实际业务流程**。

## 核心文件

### 1. 客户端封装

- **`app/external_services/fal.py`** - 统一的 fal.ai 客户端包装器
  - 支持图片、TTS、视频生成
  - 使用官方 `fal_client` 包
  - 提供 `FalAIClient` 类，包含 `text_to_image()`、`text_to_speech()`、`text_to_video()` 方法
  - 认证通过环境变量 `FAL_KEY` 或显式传入 `api_key`

- **`app/external_services/fal_ai.py`** - 仅图片生成的客户端（旧版？）
  - 注释说明："This module is intentionally NOT integrated into Inty backend flows yet"
  - 功能与 `fal.py` 中的图片生成部分重复

### 2. 统一图片生成 API

- **`app/external_services/text_to_image.py`** - 多提供商统一接口
  - 支持 Google Imagen、OpenAI、fal.ai 三个提供商
  - 通过模型名称前缀路由：`google/`、`openai/`、`fal-ai/` 或 `fal/`
  - 默认无前缀时路由到 fal.ai
  - 提供 `generate_text_to_image()` 函数
  - **注释说明："This module is intentionally NOT integrated into Inty backend flows yet"**

### 3. 测试支持

- **`app/external_services/fakes/fal_ai.py`** - 测试用假客户端
  - `FakeFalAIClient` 类，返回模拟结果

## 当前状态

✅ **已完成**：
- fal.ai 客户端封装
- 统一图片生成 API 框架
- 支持多提供商路由
- 测试基础设施

❌ **未完成**：
- 未接入实际业务 API 端点
- 当前后端仍使用 Google Imagen（见 `app/api/v1/endpoints/agents.py` 中的 `text_to_image` 函数）
- 配置中未设置 fal.ai 模型（见 `app/core/config.py`）

## 使用方式

如需使用 fal.ai 生成图片，调用：

```python
from app.external_services.text_to_image import generate_text_to_image, TextToImageGenerationRequest

request = TextToImageGenerationRequest(
    model="fal-ai/flux-1.1-pro",  # 或 "fal/flux-1.1-pro"
    prompt="a cat wearing a kimono",
    num_images=1,
    provider_args={
        "api_key": "your-api-key",  # 可选，也可通过 FAL_KEY 环境变量
        "image_size": "landscape_4_3",
        "output_format": "png",
    }
)
result = generate_text_to_image(request)
```

## 注意事项

1. 存在两个 fal.ai 客户端文件（`fal.py` 和 `fal_ai.py`），功能重复，建议统一使用 `fal.py`
2. `text_to_image.py` 中导入的是 `fal_ai.py` 的 `FalAIClient`，可考虑改为使用 `fal.py` 中的版本
3. 需要配置 `FAL_KEY` 环境变量或通过 `provider_args` 传入 API key

---

CREATED_BY_AGENT
