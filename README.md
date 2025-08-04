# InTy Backend

InTy 是一个基于 FastAPI 和 PostgreSQL 的 AI 聊天应用后端，集成了 LangChain 和 LangGraph 技术栈，支持多种 AI 模型和智能体管理。项目采用现代化的异步编程架构，提供完整的 AI 对话解决方案和商业化订阅服务。

## 系统架构

```
                               HTTP Clients
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────┐
│                FastAPI application (app/main.py)                   │
│ • loads config, logging                                            │
│ • CORS & error middleware                                         │
│ • startup: init Firebase, cache_service, background_task_service,  │
│   keep_talking_service, agent_manager                              │
└───────────────┬────────────────────────────────────────────────────┘
                │
                ▼
          ┌──────────────┐
          │ API Routers  │  (/api/v1/endpoints/* – auth, users, agents,
          └───────┬──────┘   chats, settings, report, subscription, evaluation…)
                  │
                  ▼
          ┌──────────────────────────┐
          │        Services          │
          │ agent_service, chat_service, user_service,
          │ voice_service, notification_service, …                     │
          └──────┬───────────────────┘
                 │
        ┌────────▼────────┐         ┌───────────────────────────┐
        │ Core Agent       │         │ Data Access Layer         │
        │ (LangChain /     │         │ • SQLAlchemy models       │
        │  LangGraph /     │         │ • async sessions          │
        │  embeddings /    │         │ • chat_history_service    │
        │  GCS / cache )   │         └───────────┬──────────────┘
        └───────┬─────────┘                     │
                │                               ▼
                │                    ┌────────────────────┐
                │                    │ PostgreSQL DB      │
                │                    │ (app data + chat   │
                │                    │  history store)    │
                │                    └────────────────────┘
                │
                ▼
      ┌────────────────────────────────────────────┐
      │  Support services                          │
      │  • cache_service (in‑memory cache)         │
      │  • background_task_service (thread pool)   │
      │  • keep_talking_service (idle chat monitor)│
      └────────────────────────────────────────────┘
                │
                ▼
┌────────────────────────────────────────────────────────────────────┐
│                    External Integrations                           │
│ OpenAI/LLM APIs, Google Search API, Google Cloud Storage, Firebase │
│ Google OAuth & Google Play, ElevenLabs voice, SMS/Notification svc │
└────────────────────────────────────────────────────────────────────┘
```

GCS public access

<img width="800" alt="image" src="https://github.com/user-attachments/assets/9230dc1f-1430-467b-b12e-bfba1def3922" />

## 在本地开发环境启动 App

```bash
git clone https://github.com/NascentCore/inty-backend.git
cd inty-backend

python -m venv venv
source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt

# Copy the sample config file to the actual file name
# And edit config.yaml to set the correct settings.
cp config.yaml.example config.yaml
```

### 环境要求

config.yaml 指明依赖服务的配置选项

* PostgreSQL 12+ (需要 pgvector 扩展)
* Redis（可选，用于缓存）
* Google Cloud Storage 账户
* Google Play
* Google OAuth
* JWT 密钥
* 相关 AI 模型 API 密钥 (OpenRouter ElevenLabs API Key)

### 初始化数据库

数据库结构见 [app/models](app/models) 下各个 python 代码文件中表结构定义数据结构

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

### 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务器将在 <http://localhost:8000> 运行
启动服务器后，可以访问以下地址查看 API 文档：

* **Swagger UI**: <http://localhost:8000/docs>
* **ReDoc**: <http://localhost:8000/redoc>
* **OpenAPI JSON**: <http://localhost:8000/api/v1/openapi.json>

## 部署

### 生产环境部署

TODO: 只保留一种就够了！

1. **配置生产环境**

```bash
# 设置生产配置；编辑生产环境配置
cp config.yaml.example config.yaml
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

## 开发指南

```bash
# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 数据库迁移
alembic revision --autogenerate -m "描述"
alembic upgrade head

# Setting python path when running tests
PYTHONPATH=/Users/yzhao/Workspace/NascentCore/inty-backend \
    pytest app/core/agent/agent_test.py -v
```

## 服务帐号密钥生成

配置文件中需要配置 GCS 和 FireBase 的服务帐号密钥

### Firebase 服务账号密钥生成

  1. 进入 Firebase Console：
    - 访问 <https://console.firebase.google.com/>
    - 选择项目（Inty）
  2. 生成服务账号密钥：
    - 在项目设置 -> 服务账号 -> 生成新的私钥
    - 下载的文件重命名为：inty-firebase-key.json

### Google Cloud Storage 服务账号密钥生成

  1. 进入 Google Cloud Console：
    - 访问 <https://console.cloud.google.com/>
    - 选择项目（Inty）
  2. 创建服务账号：
    - 设置 “roles/storage.admin” 角色
    - 点击创建的服务帐号 -> 密钥 -> 创建新密钥
    - 下载的文件重命名为：inty-backend-key.json

## 功能特性

TODO: 这部分内容应该浓缩成对读者有价值的关键信息，而不是罗列低效信息。

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
