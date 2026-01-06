# 运营平台设计笔记

## eval_app/ - 独立评测平台

### 概述

`eval_app/` 是一个独立的 FastAPI 应用，专门用于内部运营工具。它的设计目标是：

- **独立部署**：与主应用 `app/` 完全分离，运行在独立端口（8001）
- **复刻现有功能**：复刻目前评测平台的使用情况，满足现有运营需求
- **独立于主应用**：不依赖主应用的后台服务，但共享数据库和服务层代码

### 架构设计

#### 应用结构

```text
eval_app/
├── main.py                  # FastAPI 应用入口
├── api/                     # API 路由层
│   ├── deps.py              # 依赖注入（复用主应用）
│   └── v1/
│       ├── router.py        # 路由注册
│       └── endpoints/       # 端点实现
│           ├── evaluation.py  # Evaluation 专用端点
│           ├── agents.py      # Agent 端点（共享）
│           ├── chats.py       # Chat 端点（共享）
│           ├── users.py       # User 端点（共享）
│           └── ...
├── services/                # 服务代理层
│   ├── agent_service_proxy.py
│   ├── chat_service_proxy.py
│   └── ...
├── core/                    # 核心配置
│   └── config.py            # 配置（复用主应用）
└── static/                  # 静态文件
    └── evaluation/          # Evaluation 前端构建产物
```

#### 与主应用的关系

```text
┌─────────────────────────────────────────┐
│          eval_app/ (端口 8001)           │
│  - Evaluation 专用 API                  │
│  - 共享端点（Agent、Chat、User 等）      │
│  - Evaluation 前端静态文件              │
└─────────────────────────────────────────┘
              ↓ [直接调用]
┌─────────────────────────────────────────┐
│          app/services/                   │
│  - agent_service                        │
│  - chat_service                         │
│  - evaluation_service                   │
│  - user_service                         │
└─────────────────────────────────────────┘
              ↓ [共享连接]
┌─────────────────────────────────────────┐
│      生产数据库 (Cloud SQL)              │
└─────────────────────────────────────────┘
```

**关键设计点**：

1. **共享服务层**：`eval_app` 通过服务代理直接调用 `app/services/` 中的服务类

2. **共享数据库**：两个应用使用相同的数据库配置和连接

3. **共享认证**：使用相同的 JWT 密钥，token 可以跨应用使用

4. **共享配置**：使用相同的 `config.yaml` 和配置读取逻辑

### 功能范围

#### Evaluation 专用端点

所有 `/api/v1/evaluation/*` 端点，包括：

- ✅ 评测会话管理（创建、启动、监控、结果查看）
- ✅ 评测模板管理（创建、编辑、删除）
- ✅ 用户数据分析（注册统计、活跃度、热门角色等）
- ✅ 评测专用智能体管理

#### 共享端点

以下端点通过服务代理调用主应用的服务层：

- `/api/v1/ai/agents/*` - Agent 管理（创建、编辑、删除、搜索）
- `/api/v1/chats/*` - 聊天相关（会话管理、消息发送）
- `/api/v1/users/*` - 用户管理（搜索、查询）
- `/api/v1/images` - 图片上传
- `/api/v1/text-to-speech/list-voices` - 语音列表
- `/api/v1/character-themes/*` - 角色主题管理

### 前端集成

**前端位置**：`evaluation/` 目录

**构建与部署**：

1. 前端构建产物输出到 `eval_app/static/evaluation/`
2. `eval_app` 通过 FastAPI 静态文件服务提供前端访问
3. 访问路径：`http://localhost:8001/evaluation`

**构建脚本**：

```bash
cd evaluation
./build.sh  # 自动将产物复制到 eval_app/static/evaluation/
```

### 启动方式

#### 开发模式

```bash
./eval_app/start.sh --dev
```

这将：

1. 检查并运行数据库迁移
2. 构建 evaluation 前端（如果存在）
3. 在 `http://localhost:8001` 启动 IntyEval（带热重载）

#### 生产模式

```bash
./eval_app/start.sh
```

在 `http://localhost:8001` 启动 IntyEval（无热重载）

#### 手动启动

```bash
# 确保数据库迁移已完成
alembic upgrade head

# 启动应用
uvicorn eval_app.main:app --host 0.0.0.0 --port 8001
```

### 访问地址

- **API 文档**：`http://localhost:8001/docs`（仅在 debug 模式下）
- **Evaluation 前端**：`http://localhost:8001/evaluation`
- **健康检查**：`http://localhost:8001/`

### 配置

`eval_app` 使用与主应用相同的配置系统：

- **配置文件**：`config.yaml`（在项目根目录）
- **配置读取**：`app/core/config.py`（共享）
- **数据库配置**：与主应用相同
- **认证配置**：与主应用相同（JWT 密钥）

### 技术实现细节

#### 服务代理模式

`eval_app` 使用服务代理模式，通过 `eval_app/services/` 中的代理函数直接调用 `app/services/` 中的服务类：

```python
# eval_app/services/agent_service_proxy.py
from app.services import agent_service

async def get_user_agents(db, current_user, ...):
    return await agent_service.get_user_agents(db, current_user=current_user, ...)
```

**优势**：

- 代码复用：无需重复实现业务逻辑
- 一致性：确保两个应用使用相同的业务规则
- 维护性：业务逻辑变更只需修改一处

#### 依赖注入复用

`eval_app/api/deps.py` 直接导入主应用的依赖函数：

```python
from app.api.deps import (
    get_async_db,
    get_current_active_user,
    get_current_user,
    ...
)
```

**优势**：

- 认证逻辑一致
- 数据库会话管理一致
- 减少代码重复

### 与主应用的区别

| 特性 | 主应用 (app/) | 运营平台 (eval_app/) |
| :--- | :------------ | :------------------- |
| **端口** | 8000 | 8001 |
| **功能范围** | 用户面向功能 + 运营功能 | 仅运营工具 |
| **前端服务** | 不包含前端 | 服务 evaluation 前端 |
| **API 范围** | 完整 API | Evaluation + 共享端点 |
| **部署** | 生产环境 | 内部工具 |

### 当前状态

**已完成**：

- ✅ 独立 FastAPI 应用框架
- ✅ Evaluation 专用端点
- ✅ 共享端点（Agent、Chat、User 等）
- ✅ 前端静态文件服务
- ✅ 服务代理层实现
- ✅ 数据库迁移集成
- ✅ 启动脚本

**待完善**：

- ⚠️ 数据分离（当前直接访问生产数据库）
- ⚠️ 权限系统（当前所有功能对所有用户开放）
- ⚠️ 审核工作流（核心缺失功能）
- ⚠️ 发布管理（核心缺失功能）

### 设计目标

1. **独立性**：可以独立部署和运行，不依赖主应用的后台服务

2. **功能完整性**：复刻现有评测平台的所有功能

3. **代码复用**：通过服务代理复用主应用的业务逻辑

4. **安全性**：独立的认证和授权机制（待实现）

5. **可维护性**：清晰的代码结构和职责划分

### 开发注意事项

1. **导入路径**：`eval_app` 需要能够导入 `app/` 目录下的模块

2. **数据库连接**：确保两个应用使用相同的数据库配置

3. **认证 Token**：两个应用使用相同的 JWT 密钥，token 可以跨应用使用

4. **CORS 配置**：`eval_app` 可能需要不同的 CORS 配置

5. **前端构建**：修改前端代码后需要重新构建并复制到 `eval_app/static/evaluation/`

### 未来改进方向

1. **数据分离**：使用 BigQuery + Read Replica 进行数据查询分离

2. **权限系统**：实现基于角色的访问控制（RBAC）

3. **审核工作流**：实现完整的角色审核流程

4. **发布管理**：实现角色发布和版本管理

5. **完全独立**：逐步减少对主应用的依赖，实现真正的独立部署

---

本文档由 AI 助手创建 (CREATED_BY_AGENT)
