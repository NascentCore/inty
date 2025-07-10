# InTy Backend

InTy 是一个基于 FastAPI 和 PostgreSQL 的 AI 聊天应用后端，集成了 LangChain 和 LangGraph 技术栈，支持多种 AI 模型和智能体管理。项目采用现代化的异步编程架构，提供完整的 AI 对话解决方案和商业化订阅服务。

## 功能特性

### 🤖 AI 智能体系统
- **基于 LangGraph 的智能体引擎**：支持复杂的对话流程和状态管理
- **多模型支持**：集成 OpenAI、Anthropic、Google AI 等主流模型
- **智能体管理**：创建、编辑、发布和管理 AI 角色
- **提示词模板系统**：支持动态提示词生成和模板化管理
- **记忆系统**：基于 PostgreSQL 的持久化对话记忆
- **Keep Talking 功能**：智能主动延续对话，提升用户体验

### 🔐 用户认证与授权
- **多种认证方式**：手机号、Google OAuth、游客模式
- **JWT 令牌认证**：安全的身份验证机制
- **Firebase 集成**：完整的身份验证服务
- **用户权限管理**：基于角色的访问控制

### 💰 商业化订阅系统
- **Google Play 订阅集成**：支持月度和季度订阅
- **订阅状态管理**：实时跟踪用户订阅状态
- **使用量统计**：详细的功能使用统计和限制
- **收据验证**：安全的购买验证机制
- **订阅权益管理**：灵活的功能权限配置

### 💬 聊天功能
- **实时消息传输**：高性能的异步消息处理
- **多媒体支持**：文本、语音、图片消息
- **聊天设置管理**：个性化的对话配置
- **多语言支持**：国际化的用户界面
- **消息推送**：实时通知系统

### 🛠 系统功能
- **资源管理**：集成 Google Cloud Storage 的文件管理
- **日志监控**：完整的日志记录和错误追踪
- **API 文档**：自动生成的 OpenAPI 文档
- **数据库迁移**：版本化的数据库管理
- **性能优化**：异步处理和连接池优化

## 技术栈

### 🚀 核心框架
- **Python 3.8+** - 编程语言
- **FastAPI** - 高性能异步 Web 框架
- **PostgreSQL** - 关系型数据库
- **SQLAlchemy** - 异步 ORM 框架
- **Alembic** - 数据库迁移工具
- **Uvicorn** - ASGI 服务器

### 🤖 AI 技术栈
- **LangChain** - AI 应用开发框架
- **LangGraph** - 智能体状态管理和工作流
- **OpenAI API** - GPT 模型集成
- **Anthropic API** - Claude 模型集成
- **Google AI** - Gemini 模型集成
- **LangMem** - 记忆管理系统
- **向量数据库** - pgvector 扩展

### 🔐 身份认证
- **JWT** - 令牌认证
- **Google OAuth** - 第三方登录
- **Firebase** - 身份验证服务
- **bcrypt** - 密码哈希

### ☁️ 云服务
- **Google Cloud Storage** - 文件存储
- **Google Search API** - 搜索功能
- **Google Play Developer API** - 订阅管理
- **Firebase Cloud Messaging** - 消息推送

### 🛠 开发工具
- **Pydantic** - 数据验证
- **PyYAML** - 配置管理
- **Loguru** - 日志系统
- **pytest** - 测试框架

## 数据库结构

### 核心实体
- **users** - 用户基础信息
- **agents** - AI 智能体配置
- **chats** - 聊天会话
- **messages** - 聊天消息
- **chat_settings** - 聊天设置

### 订阅系统
- **subscription_plans** - 订阅计划
- **user_subscriptions** - 用户订阅
- **subscription_transactions** - 订阅交易记录
- **subscription_usage** - 使用统计
- **subscription_features** - 订阅权益

### 功能模块
- **agent_followers** - 智能体关注关系
- **notification** - 消息通知
- **device_tokens** - 设备令牌
- **report** - 举报记录
- **resources** - 资源管理
- **settings** - 用户设置

## 开发环境设置

### 1. 克隆项目
```bash
git clone https://github.com/NascentCore/inty-backend.git
cd inty-backend
```

### 2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置环境变量
```bash
cp config.yaml.example config.yaml
# 编辑 config.yaml 文件，设置必要的配置：
# - 数据库连接信息
# - JWT 密钥
# - Google OAuth 配置
# - AI 模型 API 密钥
# - Google Cloud Storage 配置
# - Google Play 订阅配置
```

### 5. 初始化数据库
```bash
# 创建数据库
createdb inty_db

# 运行数据库迁移
alembic upgrade head

# 初始化订阅计划（可选）
python scripts/init_subscription_plans.py
```

### 6. 运行开发服务器
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务器将在 http://localhost:8000 运行

## API 文档

启动服务器后，可以访问以下地址查看 API 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## 项目结构

```
inty-backend/
├── alembic/                    # 数据库迁移文件
├── app/
│   ├── api/                   # API 路由层
│   │   ├── deps.py           # 依赖注入
│   │   └── v1/               # API v1 版本
│   │       ├── api.py        # 路由汇总
│   │       └── endpoints/    # 各模块端点
│   │           ├── agents.py      # 智能体管理
│   │           ├── auth.py        # 用户认证
│   │           ├── chats.py       # 聊天功能
│   │           ├── subscription.py # 订阅管理
│   │           └── ...
│   ├── core/                  # 核心系统
│   │   ├── agent/            # AI 智能体核心
│   │   │   ├── agent.py      # 智能体引擎
│   │   │   ├── memory.py     # 记忆系统
│   │   │   └── prompt_template.py # 提示词模板
│   │   ├── config.py         # 配置管理
│   │   ├── security.py       # 安全认证
│   │   └── firebase.py       # Firebase 集成
│   ├── db/                    # 数据库
│   │   ├── base.py           # 数据库基类
│   │   └── session.py        # 会话管理
│   ├── models/                # 数据库模型
│   │   ├── user.py           # 用户模型
│   │   ├── agent.py          # 智能体模型
│   │   ├── subscription.py   # 订阅模型
│   │   └── ...
│   ├── schemas/               # Pydantic 模型
│   ├── services/              # 业务逻辑层
│   │   ├── agent_service.py       # 智能体服务
│   │   ├── subscription_service.py # 订阅服务
│   │   ├── google_play_service.py  # Google Play 服务
│   │   ├── keep_talking_service.py # Keep Talking 服务
│   │   └── ...
│   ├── middleware/            # 中间件
│   ├── utils/                 # 工具函数
│   └── main.py               # 应用入口
├── docs/                      # 文档
│   ├── Google_Play_Subscription_Setup.md
│   ├── KEEP_TALKING_功能说明.md
│   └── PROMPT_TEMPLATE_SYSTEM.md
├── scripts/                   # 脚本
├── testing/                   # 测试相关
├── config.yaml.example        # 配置文件模板
├── requirements.txt           # 项目依赖
└── README.md                 # 项目文档
```

## 核心功能说明

### Keep Talking 智能延续对话
- **自动监控**：定期检查闲置会话
- **智能触发**：基于时间和上下文的智能判断
- **上下文延续**：生成相关的延续对话内容
- **频次控制**：防止过度发送消息

### 提示词模板系统
- **模板化管理**：使用 string.Template 进行模板处理
- **变量替换**：支持动态变量和默认值
- **模板验证**：确保模板格式正确
- **灵活配置**：支持多种提示词策略

### 订阅管理系统
- **Google Play 集成**：完整的订阅生命周期管理
- **收据验证**：安全的购买验证机制
- **权益管理**：基于订阅的功能权限控制
- **使用统计**：详细的功能使用监控

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
- Python 3.8+
- PostgreSQL 12+
- Redis（可选，用于缓存）
- Google Cloud Storage 账户
- 相关 AI 模型 API 密钥

## 开发指南

### 常用命令
```bash
# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 数据库迁移
alembic revision --autogenerate -m "描述"
alembic upgrade head

# 运行测试
pytest

# 代码格式化
black app/
isort app/
```

### 配置说明
项目使用 YAML 配置文件，包含：
- 应用基础配置
- 数据库连接信息
- AI 模型配置
- 第三方服务密钥
- 日志配置

**重要**: 请确保复制 `config.yaml.example` 并配置实际的数据库连接和 API 密钥。

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request