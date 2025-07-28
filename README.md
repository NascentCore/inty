# InTy Backend

InTy 是一个基于 FastAPI 和 PostgreSQL 的 AI 聊天应用后端，集成了 LangChain 和 LangGraph 技术栈，支持多种 AI 模型和智能体管理。项目采用现代化的异步编程架构，提供完整的 AI 对话解决方案和商业化订阅服务。

Quick pointers:

* API 文档（Swagger）：<https://dev.inty.sxwl.ai/docs>

## 功能特性

### 🤖 AI 智能体系统

* **基于 LangGraph 的智能体引擎**：支持复杂的对话流程和状态管理
* **多模型支持**：集成 OpenAI、Anthropic、Google AI 等主流模型
* **智能体管理**：创建、编辑、发布和管理 AI 角色
* **提示词模板系统**：支持动态提示词生成和模板化管理
* **记忆系统**：基于 PostgreSQL 的持久化对话记忆
* **Keep Talking 功能**：智能主动延续对话，提升用户体验

### 🔐 用户认证与授权

* **多种认证方式**：手机号、Google OAuth、游客模式
* **JWT 令牌认证**：安全的身份验证机制
* **Firebase 集成**：完整的身份验证服务
* **用户权限管理**：基于角色的访问控制

### 💰 商业化订阅系统

* **Google Play 订阅集成**：支持月度和季度订阅
* **订阅状态管理**：实时跟踪用户订阅状态
* **使用量统计**：详细的功能使用统计和限制
* **收据验证**：安全的购买验证机制
* **订阅权益管理**：灵活的功能权限配置

### 💬 聊天功能

* **实时消息传输**：高性能的异步消息处理
* **AI 语音回复**：集成 ElevenLabs API 的智能语音合成
* **语音自动播放**：可配置的语音自动播放和手动播放
* **语音缓存优化**：智能缓存机制，降低API调用成本
* **多媒体支持**：文本、语音、图片消息
* **聊天设置管理**：个性化的对话配置
* **多语言支持**：国际化的用户界面
* **消息推送**：实时通知系统

### 🛠 系统功能

* **资源管理**：集成 Google Cloud Storage 的文件管理
* **日志监控**：完整的日志记录和错误追踪
* **API 文档**：自动生成的 OpenAPI 文档
* **数据库迁移**：版本化的数据库管理
* **性能优化**：异步处理和连接池优化

## 技术栈

### 🚀 核心框架

* **Python 3.8+** - 编程语言

* **FastAPI** - 高性能异步 Web 框架
* **PostgreSQL** - 关系型数据库
* **SQLAlchemy** - 异步 ORM 框架
* **Alembic** - 数据库迁移工具
* **Uvicorn** - ASGI 服务器

### 🤖 AI 技术栈

* **LangChain** - AI 应用开发框架

* **LangGraph** - 智能体状态管理和工作流
* **OpenAI API** - GPT 模型集成
* **Anthropic API** - Claude 模型集成
* **Google AI** - Gemini 模型集成
* **LangMem** - 记忆管理系统
* **向量数据库** - pgvector 扩展

### 🔐 身份认证

* **JWT** - 令牌认证
* **Google OAuth** - 第三方登录
* **Firebase** - 身份验证服务
* **bcrypt** - 密码哈希

### ☁️ 云服务

* **Google Cloud Storage** - 文件存储和语音文件管理
* **Google Search API** - 搜索功能
* **Google Play Developer API** - 订阅管理
* **Firebase Cloud Messaging** - 消息推送
* **ElevenLabs API** - 高质量语音合成服务

### 🛠 开发工具

* **Pydantic** - 数据验证
* **PyYAML** - 配置管理
* **Loguru** - 日志系统
* **pytest** - 测试框架

## 数据库结构

见 [app/models](app/models) 下各个 python 代码文件中表结构定义数据结构

## 在本地开发环境启动 App

### 1. 克隆项目

```bash
git clone https://github.com/NascentCore/inty-backend.git
cd inty-backend
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 配置系统参数

```bash
# Copy the sample config file to the actual file name
# And edit config.yaml to set the correct settings.
cp config.yaml.example config.yaml
```

编辑 config.yaml 文件，设置必要的配置：

* 数据库连接信息
* JWT 密钥
* Google OAuth 配置
* AI 模型 API 密钥
* Google Cloud Storage 配置
* Google Play 订阅配置
* ElevenLabs API 密钥和语音配置

ElevenLabs 语音配置示例

```yaml
elevenlabs:
  api_key: "your_elevenlabs_api_key"
  model: "eleven_flash_v2_5"  # 推荐使用 Flash v2.5 模型
  voice_id: "EXAVITQu4vr4xnSDxMaL"  # 默认语音 ID
  output_format: "mp3_22050_32"  # 移动端优化格式
  enabled: true
  max_text_length: 5000
```

### 5. 初始化数据库

```bash
# Install createdb cli, used below
brew install postgresql

# Launch postgres with vector extensions
PG_PORT=15432
docker run --rm --name pg-vec-inty -p $PG_PORT:5432 \
    -e POSTGRES_PASSWORD=sxwl666! -d pgvector/pgvector:pg16
createdb -h localhost -p 15432 -U postgres inty_db

# Update database schemas
# Fill in the correct database settings to config.yaml
# The rest of configs can use the defaults, which do not affect local development.
# database:
#   db: inty_db
#   host: "localhost"
#   password: sxwl666!
#   port: 15432
#   user: postgres
alembic upgrade head

# 初始化订阅计划（可选）
python scripts/init_subscription_plans.py
```

### 6. 运行开发服务器

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务器将在 <http://localhost:8000> 运行

## API 文档

启动服务器后，可以访问以下地址查看 API 文档：

* **Swagger UI**: <http://localhost:8000/docs>
* **ReDoc**: <http://localhost:8000/redoc>
* **OpenAPI JSON**: <http://localhost:8000/api/v1/openapi.json>

## 核心功能说明

### Keep Talking 智能延续对话

TODO: 此处描述功能应该删除，实际 keep talking 并非如此处所述；
找 @cairong @donggang 了解详情。

* **自动监控**：定期检查闲置会话

* **智能触发**：基于时间和上下文的智能判断
* **上下文延续**：生成相关的延续对话内容
* **频次控制**：防止过度发送消息

### 提示词模板系统

* **模板化管理**：使用 string.Template 进行模板处理

* **变量替换**：支持动态变量和默认值
* **模板验证**：确保模板格式正确
* **灵活配置**：支持多种提示词策略

### 订阅管理系统

* **Google Play 集成**：完整的订阅生命周期管理

* **收据验证**：安全的购买验证机制
* **权益管理**：基于订阅的功能权限控制
* **使用统计**：详细的功能使用监控

### AI 语音系统

开发中

* **ElevenLabs 集成**：使用最新的 Flash v2.5 模型进行语音合成

* **智能缓存机制**：基于内容哈希的语音文件缓存，有效降低API成本
* **自动播放控制**：支持基于用户设置的语音自动播放和手动播放
* **多语音支持**：支持多种语音角色，可为不同Agent配置专属语音
* **文件管理**：自动上传语音文件到GCS，支持CDN加速
* **成本优化**：缓存复用、文件压缩、定期清理等多重成本控制措施

## 测试

运行测试：

```bash
pytest
```

## 部署

### 生产环境部署

1. **配置生产环境**

```bash
# 设置生产配置
cp config.yaml.example config.yaml
# 编辑生产环境配置
```

2. **使用 Gunicorn 部署**

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动应用
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

3. **使用 Docker 部署**

```bash
# 构建镜像
docker build -t inty-backend .

# 运行容器
docker run -p 8000:8000 -v $(pwd)/config.yaml:/app/config.yaml inty-backend
```

### 环境要求

* Python 3.8+

* PostgreSQL 12+ (需要 pgvector 扩展)
* Redis（可选，用于缓存）
* Google Cloud Storage 账户
* 相关 AI 模型 API 密钥 (OpenAI/Anthropic/Google AI)
* ElevenLabs API 账户（用于语音功能）

## 开发指南

### 常用命令

```bash
# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 数据库迁移
alembic revision --autogenerate -m "描述"
alembic upgrade head

# Setting pyhton path when running tests
PYTHONPATH=/Users/yzhao/Workspace/NascentCore/inty-backend \
    pytest app/core/agent/agent_test.py -v
```
