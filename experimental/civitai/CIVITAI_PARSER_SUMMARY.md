# Civitai 模型解析器 - 完整解决方案

＃＃概述

我创建了一个最小的Python解析器来从Civita模型页面中提取关键信息。解析器成功从URL（例如“https://civitai.com/models/1224788/prefect-illustrious-xl`.”）中提取所有请求的信息和其他有用数据”

## 文件已创建

1.**`civitai_parser.py`** - 具有核心功能的基本解析器
2.**`civitai_parser_enhanced.py`** - 增强版，具有更好的提取功能
3.**`requirements_parser.txt`** - 依赖关系
4.**`example_usage.py`** - 使用脚本示例
5.**`README_parser.md`** - 文档

## 提取的关键信息

### 所需信息 ✅

- **下载链接**：包含文件大小和类型的直接下载 URL
- **详细信息部分**：技术详细信息，例如模型类型、统计数据、评论等。
- **关于信息**：型号描述和信息
- **模型名称**：AI模型的名称
- **标签**：与模型关联的类别和标签

### 其他有用信息 ✅

- **统计**：下载计数、点赞、评论等。
- **创建者**：模型创建者信息
- **许可证**：许可证信息
- **建议设置**：建议的生成设置
- **版本信息**：型号版本信息
- **模型版本**：所有可用版本- **结构化数据**：JSON-LD结构化数据

## 输出示例```json
{
  "url": "https://civitai.com/models/1224788/prefect-illustrious-xl",
  "model_name": "Prefect illustrious XL",
  "tags": [
    "Checkpoint",
    "v3",
    "base models",
    "styles",
    "anime",
    "Checkpoint Merge",
    "girls",
    "woman",
    "Merge",
    "base model"
  ],
  "download_links": [
    {
      "url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/14538/prefectIllustriousXl.Ry5O.safetensors",
      "text": "prefect_illustrious_xl_v3.fp16.safetensors",
      "file_size": "6.61 GB",
      "file_type": "SafeTensor"
    }
  ],
  "details": {
    "Type": "Checkpoint Merge",
    "Stats": "460",
    "Reviews": "Very Positive(139)",
    "Published": "Aug 4, 2025",
    "Base Model": "Illustrious",
    "Hash": "AutoV21A66B7E7F5"
  },
  "about": "If you like my work, drop a 5 review and hit the heart icon...",
  "stats": {
    "downloads": "4.2m",
    "likes": "3.1k"
  },
  "creator": "Goofy_Ai",
  "license": "Illustrious License",
  "suggested_settings": {
    "suggested_settings": "CLIP skip 1, Samplers: Eular A, DPM++ 2M, CFG: 5-6..."
  },
  "version_info": {
    "version": "3.0"
  },
  "model_versions": [
    {
      "version": "3.0",
      "text": "v3"
    },
    {
      "version": "2.0",
      "text": "v2.0p"
    }
  ]
}
```＃＃特征

### 生成

- 处理静态 HTML 和动态 JavaScript 内容
- 从构造数据 (JSON-LD) 和 HTML 元素中提取
- 过滤掉导航元素和不相关的内容
- 处理各种页面布局和结构

### 错误处理

- 网络连接问题
- 无效的网址
- 解析错误
- 缺少内容

＃＃＃方便使用的

- 清理 JSON 输出
- Compr丰富的文档
- 使用脚本示例
- 易于扩展和定制

＃＃最合适

### 基本使用```python
from civitai_parser_enhanced import CivitaiParserEnhanced

parser = CivitaiParserEnhanced()
url = "https://civitai.com/models/1224788/prefect-illustrious-xl"
result = parser.parse_model_page(url)
print(json.dumps(result, indent=2))
```＃＃＃ 安装```bash
pip install -r requirements_parser.txt
```## 技术实现

### 关键方法

-`parse_model_page()`：主要解析方法
-`_extract_download_links()`：提取下载 URL 和元数据
-`_extract_tags()`：过滤并提取模型标签
-`_extract_details()`：获取技术细节
-`_extract_structured_data()`：提取JSON-LD数据

### 依赖关系

-`requests`: HTTP 请求
-`beautifulsoup4`: HTML 解析
-`lxml`: XML/HTML 解析器后端

## 限制和注意事项

- 解析器依赖于 HTML 结构，如果 Civita 更改其网站，则可能需要更新
- 某些信息可能不适用于所有型号
- 专为公共模型页面设计
- 使用真实的用户代理来避免被阻止

## 文件摘要

|文件 |目的|
| ---------------------------- | --------------------------------------- ||`civitai_parser.py`|基本解析器实现 |
|`civitai_parser_enhanced.py`|增强版，更好的提取 |
|`requirements_parser.txt`| Python 依赖项 |
|`example_usage.py`|使用示例 |
|`README_parser.md`|详细文档|

## 成功指标

✅ **成功提取所有请求的信息**

- 包含文件大小和类型的下载链接
- 详细信息部分
- 关于/描述信息
- 型号名称
- 标签/类别

✅ **包含其他有用信息**

- 创作者信息
- 许可证详细信息
- 建议设置
- 版本信息
- 统计数据
- 结构化数据

✅ **稳健且用户友好**

- 错误处理
- 清理 JSON 输出
- Compr大量文档
- 易于使用和扩展解析器成功提取所请求的所有关键信息，并以干净、结构化的 JSON 格式提供其他有用数据。