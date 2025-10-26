# Civitai 模型解析器

一个最小的 Python 解析器，用于从 Civita 模型页面中提取关键信息。

＃＃ 特征

从 Civita 模型页面中提取以下信息：

- **模型名称**：AI模型的名称
- **标签**：与模型关联的类别和标签
- **下载链接**：包含文件大小和类型信息的直接下载链接
- **详细信息**：技术详细信息，例如模型类型、统计数据、评论等。
- **关于**：有关模型的描述和信息
- **统计**：下载计数、点赞、评论等。
- **创建者**：模型创建者信息
- **许可证**：许可证信息
- **建议设置**：建议的生成设置- **版本信息**：型号版本信息

＃＃ 安装

1.安装所需的依赖项：```bash
pip install -r requirements_parser.txt
```＃＃ 用法

### 基本用法```python
from civitai_parser import CivitaiParser

# Initialize the parser
parser = CivitaiParser()

# Parse a model page
url = "https://civitai.com/models/1224788/prefect-illustrious-xl"
result = parser.parse_model_page(url)

# Print results
print(json.dumps(result, indent=2))
```### 示例脚本

运行示例脚本来测试解析器：```bash
python example_usage.py
```这将：

1.解析示例Civita模型页面
2. 将结果保存到JSON文件中
3.在控制台显示关键信息

## 输出格式

解析器返回一个具有以下结构的 JSON 对象：```json
{
  "url": "https://civitai.com/models/1224788/prefect-illustrious-xl",
  "model_name": "Prefect illustrious XL",
  "tags": ["anime", "woman", "girls", "styles", "base models"],
  "download_links": [
    {
      "url": "https://civitai.com/download/...",
      "text": "Download (6.46 GB)",
      "file_size": "6.46 GB",
      "file_type": "SafeTensor"
    }
  ],
  "details": {
    "Type": "Checkpoint Merge",
    "Stats": "460",
    "Reviews": "Very Positive (138)",
    "Published": "Aug 4, 2025",
    "Base Model": "Illustrious"
  },
  "about": "Model description and information...",
  "stats": {
    "downloads": "4.2m",
    "likes": "3.1k"
  },
  "creator": "GOGoofy_Ai",
  "license": "Illustrious License",
  "suggested_settings": {
    "suggested_settings": "CLIP skip 1, Samplers: Eular A, DPM++ 2M, CFG: 5-6..."
  },
  "version_info": {
    "version": "3.0"
  }
}
```## 错误处理

解析器包括以下错误处理：

- 网络连接问题
- 无效的网址
- 解析错误
- 缺少内容

如果发生错误，结果将包含`error`包含错误消息的字段。## 依赖关系

-`requests`：对于HTTP请求
-`beautifulsoup4`: 用于HTML解析
-`lxml`: XML/HTML 解析器

## 注释

- 解析器使用真实的用户代理来避免被阻止
- 它可以处理相对和绝对URL
- 重复的标签会自动删除
- 从下载链接中提取文件大小和类型
- 解析器被设计为强大的并且可以处理各种页面布局

## 限制

- 解析器依赖于 HTML 结构，如果 Civita 更改其网站布局，则可能需要更新
- 某些信息可能不适用于所有型号
- 解析器是为公共模型页面设计的，可能不一致用于private/设定内容