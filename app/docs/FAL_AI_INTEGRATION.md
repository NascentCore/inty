# fal.ai 图片生成集成情况总结

## 目标

- [ ] 集成 fal.ai api 到后端服务等 /text-to-image 接口，从而让用户可以在调用时指定模型。如 /text-to-image model='google/imagen-4-fast'
- 使用场景：
  - [ ] 免费用户、付费用户使用模型区分，降低成本、凸显付费用户权益；特别是降低些许生成效果、大幅降低生成延时来改善用户体验。
  - [ ] 角色运营时调用不同模型来达到生成的效果；特别是规避某些模型过于敏感的问题（不生成违禁内容、但是仍然被平台审核拒绝）；
        对接 @zhuoyu 编写的本地角色聊天评测和角色创建功能。目前的情况汇总：
        - Vibe-coded 代码已经提交到独立代码库 https://github.com/NascentCore/mychatplayground
        - 继续 vibe-code 多模型文生图聚合平台比较困难，所以增加手动开发的 /text-to-image api endpoint，同时支持上面其他的产品后端服务能力
        - 纯 AI 编码，人力已经无法支持接入的速度了

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

**fal.ai 当前不在生产环境使用**（政策原因：审核过严）。模型选择与 agents 端点会将 fal 模型统一替换为 Vertex / Gemini，不发起任何 fal API 调用。客户端、统一 API、配置与类型均保留，作为多 provider 接入的基础，便于日后重新启用。

✅ **已完成**：
- fal.ai 客户端封装
- 统一图片生成 API 框架
- 支持多提供商路由
- 测试基础设施
- 模型选择与端点层“永不返回/使用 fal”，仅走 Vertex / Gemini

❌ **未完成**（有意搁置）：
- 生产环境不调用 fal API；配置中若写 fal 模型会在运行时被替换为 Vertex / gemini

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

## 会议纪要

### 一次简单同步

https://applink.feishu.cn/client/message/link/open?token=AmfpyocKAMADaVtl%2FZRDTNs%3D

文生图多模型对接的能力是后端的基本功能，延伸到使用场景有 2 个
@王琢誉 内部模型测试
面向用户：降低消息生图的延时
这个与上面的内部模型测试相关
可以理解为内部模型测试是长期使用方式
降低消息生图延时是短期的试验（看降低延时是否能提升活跃度）
是一个糙快猛的上线方式
伴随着生图质量下降，但是可以让用户感知到订阅价值（cc @Charles Feng）
这里还要回答到底质量下降和延迟缩短、哪个对用户的影响更大
