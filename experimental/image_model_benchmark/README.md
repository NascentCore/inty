# CREATED_BY_AGENT

# 图像生成模型评测工具

对比不同图像生成模型的响应时间和生成效果。

## 支持的模型

| 模型 | 调用方式 | Model ID |
|------|----------|----------|
| Seedream 4.5 | OpenRouter | `bytedance-seed/seedream-4.5` |
| Gemini 2.5 Flash Image | Vertex AI | `gemini-2.5-flash-image` |
| Nano Banana Pro | Vertex AI | `gemini-3-pro-image-preview` |
| Flux.2 Pro | OpenRouter | `black-forest-labs/flux.2-pro` |
| Qwen Image Edit Max | DashScope | `qwen-image-edit-max` |

## 测试场景

### 场景1：修改外观 (edit_appearance)

修改图片中人物的发色和衣服。

- 输入：1张人物参考图 (`character.jpeg`)
- 变体：
  - 红发白裙
  - 金发黑西装
  - 紫发运动装

### 场景2：双人跳舞 (two_persons_dance)

让两张图片中的人物一起跳舞。

- 输入：2张人物参考图 (`character.jpeg`, `user.jpg`)
- 变体：
  - 舞厅华尔兹
  - 户外公园
  - 夜店派对

## 环境准备

### 1. 安装依赖

```bash
cd experimental/image_model_benchmark
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# OpenRouter API Key (用于 Seedream 和 Flux)
export OPENROUTER_API_KEY="your-openrouter-api-key"

# GCP 凭证 (用于 Gemini 和 Nano Banana)
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export GOOGLE_CLOUD_PROJECT="your-project-id"  # 可选，会从凭证文件读取

# 阿里云 DashScope API Key (用于 Qwen Image Edit)
export DASHSCOPE_API_KEY="your-dashscope-api-key"
```

### 3. 准备测试图片

将测试图片放到 `test_images/` 目录：

```
test_images/
├── character.jpeg  # AI 角色参考图
└── user.jpg        # 用户参考图（双人场景需要）
```

## 使用方法

### 查看帮助

```bash
python benchmark.py --help
```

### 列出支持的模型

```bash
python benchmark.py list-models
```

### 列出测试场景

```bash
python benchmark.py list-scenarios
```

### 运行评测

```bash
# 运行所有模型的所有场景
python benchmark.py run --all

# 运行指定模型
python benchmark.py run --model seedream
python benchmark.py run --model gemini-flash
python benchmark.py run --model nano-banana
python benchmark.py run --model flux
python benchmark.py run --model qwen-image-edit

# 运行指定场景
python benchmark.py run --all --scenario edit_appearance
python benchmark.py run --all --scenario two_persons_dance

# 运行指定场景的指定变体
python benchmark.py run --all --scenario edit_appearance --variant 0

# 不保存生成的图片
python benchmark.py run --all --no-save
```

### 生成报告

```bash
# 从结果目录生成 Markdown 报告
python benchmark.py report --dir results/20260121_172255

# 指定输出文件名
python benchmark.py report --dir results/20260121_172255 --output benchmark_report.md
```

报告包含：
- 汇总表格（平均耗时、成功率、平均图片大小）
- 按场景和变体分组的详细结果
- 生成图片的对比展示

## 输出

### 结果目录

运行评测后，结果保存在 `results/<timestamp>/` 目录：

```
results/20250121_143000/
├── results.json                           # JSON 格式的详细结果
├── seedream_edit_appearance_红发白裙_xxx.jpg
├── gemini-flash_edit_appearance_红发白裙_xxx.jpg
├── ...
```

### 结果示例

```
=== 图像生成模型评测 ===

场景: 修改外观
描述: 修改图片中人物的发色和衣服
已加载 1 张测试图片

变体: 红发白裙 - 红色头发 + 白色连衣裙

  Seedream 4.5
  成功 - 12345ms, 245.3KB

  Gemini 2.5 Flash Image
  成功 - 8765ms, 312.1KB

  Nano Banana Pro
  成功 - 15432ms, 287.6KB

  Flux.2 Pro
  成功 - 18901ms, 356.2KB

┌─────────────────────┬──────────┬────────────┬─────────┐
│ 模型                │ 耗时(ms) │ 大小(KB)   │ 状态    │
├─────────────────────┼──────────┼────────────┼─────────┤
│ Seedream 4.5        │ 12,345   │ 245.3      │ ✓       │
│ Gemini 2.5 Flash    │ 8,765    │ 312.1      │ ✓       │
│ Nano Banana Pro     │ 15,432   │ 287.6      │ ✓       │
│ Flux.2 Pro          │ 18,901   │ 356.2      │ ✓       │
└─────────────────────┴──────────┴────────────┴─────────┘

=== 评测完成 ===
```

## 评测指标

- **total_time_ms**: 总响应时间（毫秒）
- **first_response_time_ms**: 首次响应时间（毫秒）
- **image_size_kb**: 生成图片大小（KB）
- **success**: 是否成功
- **error_message**: 错误信息（如有）

## 目录结构

```
image_model_benchmark/
├── README.md                 # 本文件
├── requirements.txt          # Python 依赖
├── config.py                 # 配置管理
├── benchmark.py              # CLI 主入口
├── scenarios.py              # 测试场景定义
├── models/
│   ├── __init__.py
│   ├── base.py              # 抽象基类
│   ├── openrouter.py        # OpenRouter 实现
│   └── vertexai.py          # Vertex AI 实现
├── results/                  # 评测结果输出
└── test_images/              # 测试图片目录
```
