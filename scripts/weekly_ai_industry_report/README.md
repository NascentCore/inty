# AI行业周报生成器

这个工具使用Google Custom Search API搜索过去一周的AI行业新闻，然后使用Gemini API生成综合摘要报告。

## 📁 项目结构

这是一个自包含的工具包，包含以下文件：

```
scripts/weekly_ai_industry_report/
├── __init__.py                    # 包初始化文件
├── weekly_ai_industry_report.py  # 主程序
├── test_weekly_ai_report.py      # 测试套件
├── example_usage.py              # 使用示例
├── requirements.txt              # 依赖包列表
├── setup.py                     # 安装配置
├── install.sh                   # 自动安装脚本
└── README.md                    # 本文档
```

## 功能特性

- 🔍 使用Google Custom Search API搜索最近7天的AI相关新闻
- 🤖 使用Gemini API智能分析和总结新闻内容
- 📊 支持多种搜索查询，确保全面覆盖AI行业动态
- 📄 生成结构化的JSON报告文件
- 🌐 支持中文输出，符合中文用户习惯

## 环境配置

### 1. 获取API密钥

#### Google Custom Search API
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 在"API和服务"中启用"Custom Search JSON API"
4. 在"凭据"中创建API密钥

#### Custom Search Engine (CSE)
1. 访问 [Programmable Search Engine](https://programmablesearchengine.google.com/controlpanel/all)
2. 点击"添加"创建新的搜索引擎
3. 设置为搜索整个网络
4. 在设置页面找到"搜索引擎ID"

#### Gemini API
1. 访问 [Google AI Studio](https://aistudio.google.com/)
2. 创建新项目并获取API密钥

### 2. 设置环境变量

```bash
# Linux/macOS
export GOOGLE_CSE_API_KEY="your_google_cse_api_key"
export GOOGLE_CSE_ID="your_custom_search_engine_id"
export GEMINI_API_KEY="your_gemini_api_key"

# Windows
set GOOGLE_CSE_API_KEY="your_google_cse_api_key"
set GOOGLE_CSE_ID="your_custom_search_engine_id"
set GEMINI_API_KEY="your_gemini_api_key"
```

## 快速安装

### 方法1：使用自动安装脚本（推荐）

```bash
cd scripts/weekly_ai_industry_report
./install.sh
```

### 方法2：手动安装

```bash
cd scripts/weekly_ai_industry_report
pip install -r requirements.txt
```

### 方法3：作为Python包安装

```bash
cd scripts/weekly_ai_industry_report
pip install -e .
```

## 使用方法

### 基本使用

```bash
cd scripts/weekly_ai_industry_report
python3 weekly_ai_industry_report.py
```

### 作为模块使用

```python
from weekly_ai_industry_report import AIIndustryReporter

reporter = AIIndustryReporter()
report = reporter.generate_weekly_report()
```

### 输出示例

```
🤖 AI行业周报生成器启动中...
==================================================
📅 报告日期: 2024-01-15T10:30:00
📰 发现文章: 15 篇

==================================================
🔥 AI行业周报总结 🔥
==================================================

基于过去一周的AI行业动态，以下是主要发展趋势：

1. 技术突破
- 新的多模态AI模型发布，在图像理解和文本生成方面取得重大进展
- 开源社区推出了多个轻量级模型，降低了AI应用的门槛

2. 企业动态
- 多家科技公司宣布在AI领域的重大投资
- 传统行业开始大规模采用AI解决方案

3. 政策法规
- 多个国家发布了AI治理新政策
- 数据隐私保护法规进一步完善

📄 完整报告已保存至: ai_weekly_report_20240115.json
```

## 输出文件

脚本会生成一个JSON格式的报告文件，包含：

- `success`: 报告生成是否成功
- `report_date`: 报告生成时间
- `articles_found`: 发现的文章数量
- `summary`: Gemini生成的摘要
- `sources`: 新闻来源列表

## 自定义配置

可以通过修改脚本中的以下参数来自定义搜索：

- `query`: 搜索关键词
- `days`: 搜索时间范围（天数）
- `num_results`: 每个查询的最大结果数

## 注意事项

1. Google Custom Search API有每日免费配额限制
2. Gemini API有使用频率限制
3. 确保网络连接稳定，API调用可能需要一些时间
4. 建议在非高峰时段运行以获得更好的性能

## 故障排除

### 常见错误

1. **Missing required environment variables**
   - 检查环境变量是否正确设置
   - 确保变量名拼写正确

2. **No search results found**
   - 检查Google Custom Search API配置
   - 验证CSE ID是否正确
   - 确认API密钥有效

3. **Gemini summarization error**
   - 检查Gemini API密钥
   - 确认API配额未超限

### 调试模式

可以通过修改日志级别来获取更详细的调试信息：

```python
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
```

## 许可证

此工具遵循项目整体许可证。