# 系统架构

## 概述

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
