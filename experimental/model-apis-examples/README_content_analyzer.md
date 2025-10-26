# 内容分析器

一个Python prgram，使用Google的Gemini 2.5 Flash LLM API 分析文本和图像的各种内容定义。

＃＃特征

- 分析多个内容类别的文本和图像
- 可定制描述的内容定义，标记标签和
- Pr 每个内容类别基于可得性的评分（0.0到1.0）
- 标记内容的可配置阈值
- 支持来自 JSON 文件加载/保存内容定义
- 调整自动图像大小以实现最佳API性能

＃＃安装

1.安装依赖项：```bash
uv add google-genai pillow
```2.设置你的双子座API键：```bash
export GEMINI_API_KEY="your_api_key_here"
```＃＃ 用法

### 基本用法

分析文本内容：```bash
uv run content_analyzer.py --content "This is some text to analyze" --type text
```分析图像内容：```bash
uv run content_analyzer.py --content path/to/image.jpg --type image
```### 使用自定义定义

从 JSON 文件加载定义：```bash
uv run content_analyzer.py --content "text to analyze" --type text --definitions my_definitions.json
```添加单个定义：```bash
uv run content_analyzer.py --content "text to analyze" --type text --add-definition "custom_label" "description of what this label means"
```### 调整灵敏度

设置自定义阈值（默认为 0。5）：```bash
uv run content_analyzer.py --content "text to analyze" --type text --threshold 0.7
```### 保存定义

将当前定义保存到文件中：```bash
uv run content_analyzer.py --content "text to analyze" --type text --save-definitions my_definitions.json
```## 内容定义格式

内容定义存储为 JSON ，其中标签作为键，描述作为值：```json
{
  "sexual": "any content related to sexual activity, nudity, or explicit sexual content",
  "violence": "any content depicting violence, weapons, fighting, or physical harm",
  "hate_speech": "any content promoting hatred, discrimination, or violence against specific groups"
}
```## 示例定义

prgram 附带常见内容类别的示例定义：

- 性的
- 暴力
- 仇恨
- 驱动
——戈尔
- 垃圾邮件
- 版权
- 儿童安全
- 政治的
- 医疗的
- 金融的
- 蒂蒂

## 输出格式

prgram 输出：

- 每个内容类别的 Probability 分数（0.0 至 1.0）
- 基于阈值的清除/标记状态
- 标记内容摘要
- 分析时间

输出示例：```
Analyzing text content...
Content: This is some text to analyze
--------------------------------------------------
Analysis completed in 2.34 seconds

Results:
--------------------------------------------------
sexual         | 0.023 | ✅ CLEAR
violence       | 0.156 | ✅ CLEAR
hate_speech    | 0.089 | ✅ CLEAR
drugs          | 0.012 | ✅ CLEAR
gore           | 0.034 | ✅ CLEAR
spam           | 0.067 | ✅ CLEAR
copyright      | 0.123 | ✅ CLEAR
child_safety   | 0.045 | ✅ CLEAR
--------------------------------------------------

✅ No content flagged above threshold
```## Pr 语法用法

您还可以在自己的Python代码中使用ContentAnalyzer类：```python
from content_analyzer import ContentAnalyzer

# Initialize analyzer
analyzer = ContentAnalyzer()

# Add definitions
analyzer.add_content_definition("custom", "description of custom category")

# Analyze content
results = analyzer.analyze_text("Text to analyze")
# or
results = analyzer.analyze_image("path/to/image.jpg")

print(results)
```## 注释

- 图像自动调整大小以适应512x512像素，查看最佳API性能
- prgram 使用低温 (0.1) 获得一致的结果
- Probability解析包括各种响应格式的后备机制
- 错误处理确保个别分析失败，pr图仍能继续