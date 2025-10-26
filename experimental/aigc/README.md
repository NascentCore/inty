# AI 角色生成器

一个智能 AI 代理，使用 Gemini API 生成 compr 丰富的虚构人物 pro 文件。该系统为角色扮演会话创建具有一致的物理外观、引人入胜的背景和有意义的遭遇场景的详细角色。## 测试```bash
python -m pytest test_character_generation.py
```＃＃ 特征

### 🎭 完整角色 Profiles

- **物理外观**：所有生成图像具有一致特征的详细描述
- **个性和背景**：丰富的背景故事、动机、恐惧、梦想和性格怪癖
- **遭遇场景**：角色和人类用户之间富有创意的会面场景
- **角色图像**：各种风格和场景的多个一致图像

### 🎨 多种流派和风格

- **类型**：奇幻、科幻、悬疑、浪漫、冒险、生活片段、恐怖
- **语气**：中性、严肃、幽默、神秘、前卫、快乐、明智- **图像风格**：现实、奇幻艺术、动漫、赛博朋克、卡通、绘画

### 🔧 技术特点

- **REST API**：基于 FastAPI 的 Web 服务，具有 comprehential 端点
- **CLI 界面**：用于轻松生成角色的命令行工具
- **导出格式**：JSON 和人类可读的文本格式
- **验证**：Comprehense 字符验证和一致性检查

## 快速入门

### Pr必要条件

-Python 3.8+
- 来自 Google AI Studio 的 Gemini API 密钥

＃＃＃ 安装

1. **克隆存储库**```bash
   git clone <repository-url>
   cd aigc
   ```2.**安装依赖项**```bash
   pip install -r requirements.txt
   ```3.**设置环境变量**```bash
   export GEMINI_API_KEY="your_gemini_api_key_here"
   ```＃＃＃ 用法

#### 命令行界面

使用默认设置生成角色：```bash
python cli.py "A mysterious wizard who lives in a floating tower"
```使用自定义参数生成：```bash
python cli.py "A cyberpunk hacker with neon hair" \
  --genre sci-fi \
  --tone edgy \
  --image-style cyberpunk \
  --num-images 4 \
  --export-format text \
  --output my_character.txt
```只显示人物概要：```bash
python cli.py "A wise librarian" --summary-only
```#### 网络 API

启动 API 服务器：```bash
python api.py
```API 将在“http://localhost:8000`”处可用

**生成角色：**```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "brief_description": "A mysterious wizard who lives in a floating tower",
    "genre": "fantasy",
    "tone": "mysterious",
    "image_style": "fantasy_art",
    "num_images": 4
  }'
```**获取示例请求：**```bash
curl "http://localhost:8000/examples"
```**查看 API 文档：**
请访问“http://localhost:8000/docs`”获取交互式 API 文档。## API 端点

|端点 |方法|描述 |
| ----------------- | ------ | ---------------------------------------------------- |
|`/`|获取 | API 信息和可用端点 |
|`/health`|获取 |健康检查|
|`/generate`|发布 |生成完整的字符profile |
|`/generate/async`|发布 |异步生成字符 |
|`/examples`|获取 |获取示例角色生成请求 |
|`/docs`|获取 |交互式 API 文档 |

## 字符 Profile 结构

每个生成的字符包括：

### 基本信息

- **名称**：独特的角色名称
- **年龄**：角色的年龄
- **性别**：角色的性别认同
- **物理外观**：详细的物理描述

### 背景与个性

- **起源**：角色来自哪里
- **职业**：他们做什么
- **性格特征**：关键性格特征
- **动机**：是什么驱使他们
- **恐惧**：他们害怕什么
- **梦想**：他们的愿望
- **技能**：他们擅长什么
- **怪癖**：独特的行为或习惯- **背景故事**：详细的生活史

### 遭遇场景

- **场景描述**：用户在哪里以及如何遇见角色
- **地点**：具体集合地点
- **心情**：气氛描述
- **初始对话**：角色说的第一句话
- **用户角色**：用户扮演什么角色
- **遭遇类型**：互动类型（休闲、冒险、神秘、浪漫）

### 生成的图像

- **多图像**：不同场景中角色外观一致
- **场景上下文**：每个图像设置的描述
- **图像风格**：使用的艺术风格

＃＃ 配置

系统可以通过环境变量进行配置：|变量|默认|描述 |
| -------------------------- | ------------------------------------------ | ------------------------------------------- |
|`GEMINI_API_KEY`|必填 |你的双子座 API 钥匙 |
|`DEBUG`                    | `True`|启用调试模式 |
|`HOST`                     | `0.0.0.0`| API 服务器主机 |
|`PORT`                     | `8000`| API 服务器端口 |
|`MAX_IMAGES_PER_CHARACTER` | `4`|每个角色的最大图像数 |
|`IMAGE_QUALITY`            | `high`|图像生成质量 |
|`LOG_LEVEL`                | `INFO`|日志记录级别（调试、信息、警告、错误）|
|`LOG_TO_FILE`              | `False`|启用文件日志记录 |
|`LOG_FILE`                 | `logs/character_generator.log`|日志文件路径|

## 测试

运行测试套件来验证系统：```bash
python test_character_generation.py
```这将测试：

- 具有不同类型和语气的角色生成
- 字符验证
- 导出格式
- API 功能

### 调试

使用调试工具诊断问题：```bash
python debug.py
```这个 comprehense 调试脚本将：

- 检查环境设置和依赖关系
- 测试配置加载
- 验证 Gemini API 连接
- 测试日志配置
- 验证 Pydantic 模型
- 运行完整的角色生成测试

### 日志记录

系统包括 comprehential 日志记录以供调试：

**启用详细日志记录：**```bash
export LOG_LEVEL=DEBUG
export LOG_TO_FILE=True
python cli.py "Your character description" --verbose
```**查看日志：**

- 控制台：执行过程中的实时日志
- 文件：`logs/character_generator.log`（启用后）
- 错误日志：`logs/character_generator_errors.log`（启用后）
- 详细日志：`logs/character_generator_verbose.log`（调试模式）

**日志级别：**

-`DEBUG`：详细的调试信息
-`INFO`：一般操作信息
-`WARNING`：潜在问题的警告消息
-`ERROR`：操作失败的错误消息
-`CRITICAL`：可能导致系统故障的严重错误

＃＃ 建筑学```
aigc/
├── config.py              # Configuration management
├── models.py              # Pydantic data models
├── gemini_client.py       # Gemini API client
├── character_agent.py     # Main character generation agent
├── api.py                 # FastAPI web server
├── cli.py                 # Command-line interface
├── test_character_generation.py  # Test suite
├── requirements.txt       # Python dependencies
└── README.md             # This file
```## 贡献

1. 分叉存储库
2. 创建功能分支
3. 做出改变
4.添加新功能测试
5. 提交拉取请求

＃＃ 执照

此 project 根据 MIT 许可证获得许可 - 有关详细信息，请参阅许可证文件。

＃＃ 支持

对于问题和疑问：

1.检查 API 文档：`/docs`2. 回顾测试示例
3. 在 GitHub 上打开问题

---

**注意**：该系统需要有效的 Gemini API 密钥才能运行。图像生成当前创建占位符 URL - 在 production 环境中，您将与实际图像生成服务集成。