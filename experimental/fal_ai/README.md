# fal.ai Z-Image Turbo 测试

CREATED_BY_AGENT

本目录用于测试对接 [fal.ai Z-Image Turbo API](https://fal.ai/models/fal-ai/z-image/turbo/api)。Z-Image Turbo 是由通义 MAI 开发的 6B 参数超快速文本生成图像模型。

## 目录结构

```
fal_ai/
├── README.md           # 本文件
├── requirements.txt    # Python 依赖
├── config.py           # 配置管理
├── client.py           # fal.ai 客户端封装
└── demo.py             # 命令行演示脚本
```

## 安装依赖

```bash
cd experimental/fal_ai
pip install -r requirements.txt
```

## 配置 API Key

### 方式一：环境变量（推荐）

```bash
export FAL_KEY="your-api-key"
```

### 方式二：代码中传入

```python
from client import ZImageTurboClient

client = ZImageTurboClient(api_key="your-api-key")
```

## 使用方法

### 命令行演示

```bash
# 基础用法
python demo.py "A cute cat sitting on a sofa"

# 指定图像尺寸
python demo.py "A sunset over mountains" --size landscape_16_9

# 生成多张图像
python demo.py "A futuristic city" --num-images 4

# 使用固定种子（便于复现）
python demo.py "A robot dog" --seed 42

# 完整参数示例
python demo.py "A beautiful garden" \
    --size square_hd \
    --steps 10 \
    --num-images 2 \
    --format png \
    --acceleration regular
```

### Python 代码调用

```python
from client import ZImageTurboClient

client = ZImageTurboClient()

result = client.generate(
    prompt="A cute cat sitting on a sofa",
    image_size="landscape_4_3",
    num_inference_steps=8,
    num_images=1,
)

for img in result.images:
    print(f"图像 URL: {img.url}")
    print(f"尺寸: {img.width}x{img.height}")
```

## API 参数说明

| 参数                      | 类型   | 默认值        | 说明                           |
| ------------------------- | ------ | ------------- | ------------------------------ |
| `prompt`                  | string | 必填          | 生成图像的文本提示             |
| `image_size`              | enum   | landscape_4_3 | 图像尺寸                       |
| `num_inference_steps`     | int    | 8             | 推理步数                       |
| `seed`                    | int    | 随机          | 随机种子，相同种子生成相同图像 |
| `num_images`              | int    | 1             | 生成图像数量                   |
| `enable_safety_checker`   | bool   | True          | 是否启用安全检查               |
| `enable_prompt_expansion` | bool   | False         | 是否启用提示扩展（增加费用）   |
| `output_format`           | enum   | png           | 输出格式：jpeg/png/webp        |
| `acceleration`            | enum   | none          | 加速级别：none/regular/high    |

### 图像尺寸选项

- `square_hd`: 高清正方形
- `square`: 正方形
- `portrait_4_3`: 竖版 4:3
- `portrait_16_9`: 竖版 16:9
- `landscape_4_3`: 横版 4:3
- `landscape_16_9`: 横版 16:9

## 参考链接

- [fal.ai Z-Image Turbo API 文档](https://fal.ai/models/fal-ai/z-image/turbo/api)
- [fal.ai Python 客户端文档](https://fal.ai/docs/quickstart/python)
