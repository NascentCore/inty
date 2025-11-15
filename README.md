# InTy - AI 智能伴侣平台

```text
IntelliMate: Ultimate companionship, reimagined with AI

Role-play with AI characters.
Create your own IntelliMate, powered by carefully tuned AI agents,
experience your own imagination.
```

[![Android App Tests](https://github.com/NascentCore/inty/actions/workflows/ci_android_app.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/ci_android_app.yaml)
[![Build and deploy Inty backend](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_backend.yml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_backend.yml)
[![Build and deploy IntelliMate web app](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_web_app.yml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_web_app.yml)
[![CI - Backend](https://github.com/NascentCore/inty/actions/workflows/ci_backend.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/ci_backend.yaml)
[![CI - Web App](https://github.com/NascentCore/inty/actions/workflows/ci_web_app.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/ci_web_app.yaml)
[![Sync AI characters from dev to prod](https://github.com/NascentCore/inty/actions/workflows/sync_ai_chars.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/sync_ai_chars.yaml)
[![Validate configs](https://github.com/NascentCore/inty/actions/workflows/validate_config.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/validate_config.yaml)

![](https://api.checklyhq.com/v1/badges/checks/6c7437a4-e239-473b-b08d-8285fc16ce4e?style=for-the-badge&theme=default&responseTime=true)
![](https://api.checklyhq.com/v1/badges/checks/1e149f71-dcad-49cc-a7bb-e0aecc429e6c?style=for-the-badge&theme=default&responseTime=true)

InTy 是一个基于 FastAPI 和 PostgreSQL 的 AI 聊天应用后端，集成了 LangChain 和 LangGraph 技术栈，支持多种 AI 模型和智能体管理。项目采用现代化的异步编程架构，提供完整的 AI 对话解决方案和商业化订阅服务。

## 快速开始

1. 克隆仓库并初始化子模块：

```bash
git clone --recurse-submodules git@github.com:NascentCore/inty.git
```

> 没有 SSH 权限的开发者可以改用 `https://github.com/NascentCore/inty-backend.git`。

2. 如需本地开发，请继续阅读后文的「在本地开发环境启动 App」章节获取依赖安装与环境配置步骤。

如果子模块出现脏数据（如下图所示），可以按照下面的流程重置：

<img width="480" height="436" alt="image" src="https://github.com/user-attachments/assets/23852e45-cfe6-4686-9282-c138d40bf96f" />

```bash
# 清理子模块的缓存配置
git submodule deinit -f .

# 重新拉取子模块代码
git submodule update --init --recursive
```

### Git submodule 常用操作

- **回滚到指定提交**：进入目标子模块目录后执行 `git checkout <commit-hash>`。
- **拉取子模块最新代码**：在仓库根目录执行 `git submodule update --remote --recursive`。
- **同步子模块远程信息**：在仓库根目录执行 `git submodule sync`

<img width="960" height="236" alt="image" src="https://github.com/user-attachments/assets/a3b34dad-45f4-43d0-b1fb-c066f8397bd2" />

更多进阶技巧可参考 [Git Submodule 使用指南](https://www.atlassian.com/git/articles/core-concept-workflows-and-tips)。

## 使用 Docker 容器本地运行后端服务和 Android app（适用于 app 开发者）

1. 访问 <https://docs.docker.com/desktop/setup/install/mac-install/> 安装 Docker Desktop。
2. 拷贝配置文件（config.yaml）及密钥文件到 inty-backend 代码库顶层目录。

    ```bash
    git clone git@github.com:NascentCore/inty-backend.git
    cd inty-backend

    mkdir -p .secrets

    # 拷贝 config.yaml 文件到代码库顶层目录下
    # 拷贝 cosmic-gizmo-424300-t1-6499a9d5bd94.json inty-firebase-key.json inty-backend-key.json
    # 这三个文件到代码库顶层目录下 .secrets/ 目录下
    # 然后运行下面的命令，服务在 http://localhost:8000
    docker compose up --build --detach

    # 删除所有容器及其挂载的存储卷
    # 如果不删除数据库卷，旧数据可能导致数据库 schema 不兼容而无法启动
    docker compose down --volumes
    ```

3. 创建端口映射后选择 local build type 构建 Android app：

   ```bash
   adb devices
   adb -s emulator-5554 reverse tcp:8000 tcp:8000
   ```

   <img width="600" height="1850" alt="image" src="https://github.com/user-attachments/assets/9dc4e50d-91b5-4fbf-b04c-2c154db42b29" />

## 本地启动后端服务（面向后端开发者）

使用仓库自带脚本可以一键完成数据库迁移与开发模式下的启动：

```bash
./start.sh --dev
```

脚本会执行 Alembic 迁移、初始化订阅计划，并以热加载模式启动 Uvicorn。如果只需要最小化启动流程，也可以直接运行：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 更新 openapi.json

```bash
# 调用脚本更新 app/openapi.json
export PYTHONPATH=.
python scripts/generate_openapi_json.py

# 根据 app/openapi.json 更新 app/stainless.yml
# 包括增加新的 API endpoint、删除 openapi.json 中被删除的 API endpoint 等等
```

然后，创建 Pull Request，等待 app.stainless.com 启动更新

<img width="480" height="932" alt="image" src="https://github.com/user-attachments/assets/5ba171a1-c387-404d-9ab2-c81c1c85ef74" />

## 系统架构

```ascii
                               HTTP Clients
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────┐
│                FastAPI application (app/main.py)                   │
│ • loads config, logging                                            │
│ • CORS & error middleware                                          │
│ • startup: init Firebase, cache_service, background_task_service,  │
│   agent_manager                                                     │
└─────────────────┬──────────────────────────────────────────────────┘
                  │
                  ▼
          ┌──────────────┐   (/api/v1/endpoints/* – auth, users, agents,
          │ API Routers  │    chats, settings, report, subscription, evaluation…)
          └───────┬──────┘
                  │
                  ▼
          ┌──────────────────────────────┐
          │        Services              │
          │ agent_service, chat_service, |
          │ user_service, voice_service, |
          | notification_service, …      │
          └──────┬───────────────────────┘
                 │
                 ▼
        ┌─────────────────┐         ┌───────────────────────────┐
        │ Core Agent      │         │ Data Access Layer         │
        │ (LangChain /    │         │ • SQLAlchemy models       │
        │  LangGraph /    │         │ • async sessions          │
        │  embeddings /   │         │ • chat_history_service    │
        │  GCS / cache )  │         └───────────┬───────────────┘
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

Get your GCP credential key json file to allow backend access to your GCS buckets:

<img width="3018" height="1218" alt="image" src="https://github.com/user-attachments/assets/df5c7bfb-b4ad-4d0a-b4cb-65b25c7d4560" />

## 在本地开发环境启动 App

```bash
# 若已在前文完成仓库克隆，可跳过本段
git clone https://github.com/NascentCore/inty-backend.git
cd inty-backend

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
pip install -r test_requirements.txt

# 复制示例配置并根据实际需求修改
cp devops/config.yaml.local config.yaml
```

### 环境要求

config.yaml 指明依赖服务的配置选项

- PostgreSQL 12+ (需要 pgvector 扩展)
- Redis（可选，用于缓存）
- Google Cloud Storage 账户
- Google Play
- Google OAuth
- JWT 密钥
- 相关 AI 模型 API 密钥 (OpenRouter ElevenLabs API Key)

### 初始化数据库

数据库结构见 [app/models](app/models) 下各个 python 代码文件中表结构定义数据结构

```bash
# 安装 createdb（Mac 用户示例）
brew install postgresql

# 启动带有 pgvector 扩展的 PostgreSQL 容器
PG_PORT=15432
docker run --rm --name pg-vec-inty -p $PG_PORT:5432 \
    -e POSTGRES_PASSWORD=sxwl666! -d pgvector/pgvector:pg16
createdb -h localhost -p 15432 -U postgres inty_db

# 使用 Alembic 同步数据库 schema
alembic upgrade head

# 如果需要指定非默认配置，可在命令后追加 -x config=... 覆盖 config.yaml
# 例如：alembic upgrade head -x config=devops/config.yaml.local

# 初始化订阅计划（可选）
python scripts/init_subscription_plans.py
```

使用上述命令启动服务后，服务器会在 <http://localhost:8000> 运行，可通过以下地址查看 API 文档：

- **Swagger UI**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>
- **OpenAPI JSON**: <http://localhost:8000/api/v1/openapi.json>

### 开发

```bash
# 数据库迁移
alembic revision --autogenerate -m "描述"
alembic upgrade head

# 运行单元测试示例
PYTHONPATH=$(pwd) pytest app/core/agent/agent_test.py -v
```

## 部署

### 生产环境部署

> TODO：整理本节内容，仅保留一种推荐部署流程。

1. **配置生产环境**

```bash
# 设置生产配置；编辑生产环境配置
cp devops/config.yaml.prod config.yaml
```

2. **使用 Docker 部署**

```bash
# 构建镜像
docker build -t inty-backend .

# 运行容器
docker run -p 8000:8000 -v $(pwd)/config.yaml:/app/config.yaml inty-backend
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

2. 创建服务账号（service account）：
   - 设置 “roles/storage.admin” 角色
   - 点击创建的服务帐号 -> 密钥 -> 创建新密钥
   - 下载的文件重命名为：inty-backend-key.json

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
- **OpenRouter API** - GPT 模型集成
- **Google Gemini API** - Gemini 模型集成
- **LangMem** - 记忆管理系统
- **向量数据库** - pgvector 扩展

### 🔐 身份认证

- **JWT** - 令牌认证
- **Google OAuth** - 第三方登录
- **Firebase** - 身份验证服务
- **bcrypt** - 密码哈希

### ☁️ 云服务

- **Google Cloud Storage** - 文件存储和语音文件管理
- **Google Search API** - 搜索功能
- **Google Play Developer API** - 订阅管理
- **Firebase Cloud Messaging** - 消息推送
- **ElevenLabs API** - 高质量语音合成服务
  - Gemini TTS: [pricing](https://cloud.google.com/text-to-speech/pricing?hl=en)
    - 同类型的版本和层级 2.5-flash 语音价格按 1M token 计算是 $10（语音）$2.50（文字）
    - [简单的预估语音生成成本是文字 40 倍](https://g.co/gemini/share/261be14cc60b)
