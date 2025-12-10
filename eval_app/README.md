# CREATED_BY_AGENT
# IntyEval - 内部运营工具应用

IntyEval 是一个独立的 FastAPI 应用，专门用于内部运营工具，包括评测系统和用户数据分析功能。

## 概述

IntyEval 从主 Inty 应用 (`app/`) 中分离出来，包含：

- **Evaluation 端点**: 所有 `/api/v1/evaluation/*` 端点
- **Evaluation 前端**: React/TypeScript 前端应用
- **共享端点**: 通过直接调用底层 Python 服务代码提供共享端点访问

## 架构

IntyEval 与主 Inty 应用的关系：

- **共享数据库**: 两个应用使用相同的数据库配置
- **共享服务层**: IntyEval 直接调用 `app/services/` 中的服务类
- **独立部署**: 两个应用可以独立运行在不同端口

## 启动

### 开发模式

```bash
./start_eval.sh --dev
```

这将：
1. 检查并运行数据库迁移
2. 构建 evaluation 前端（如果存在）
3. 在 `http://localhost:8001` 启动 IntyEval（带热重载）

### 生产模式

```bash
./start_eval.sh
```

在 `http://localhost:8001` 启动 IntyEval（无热重载）

### 手动启动

```bash
# 确保数据库迁移已完成
alembic upgrade head

# 启动应用
uvicorn eval_app.main:app --host 0.0.0.0 --port 8001
```

## 访问

- **API 文档**: `http://localhost:8001/docs` (仅在 debug 模式下)
- **Evaluation 前端**: `http://localhost:8001/evaluation`
- **健康检查**: `http://localhost:8001/`

## 配置

IntyEval 使用与主应用相同的配置系统：

- 配置文件: `config.yaml` (在项目根目录)
- 配置读取: `app/core/config.py` (共享)
- 数据库配置: 与主应用相同

## API 端点

### Evaluation 专用端点

所有 `/api/v1/evaluation/*` 端点，包括：

- 评测会话管理
- 评测模板管理
- 用户数据分析
- 智能体管理（评测专用）

### 共享端点

以下端点通过直接调用底层服务提供：

- `/api/v1/ai/agents/*` - Agent 管理
- `/api/v1/chats/*` - 聊天相关
- `/api/v1/users/*` - 用户管理（部分）
- `/api/v1/images` - 图片上传
- `/api/v1/text-to-speech/list-voices` - 语音列表
- `/api/v1/character-themes/*` - 角色主题

## 文件结构

```
eval_app/
├── main.py                  # 应用入口
├── api/
│   ├── deps.py              # 依赖注入（复用主应用）
│   └── v1/
│       ├── router.py        # 路由注册
│       └── endpoints/       # 端点实现
│           ├── evaluation.py  # Evaluation 端点
│           ├── agents.py      # Agent 端点（共享）
│           ├── chats.py       # Chat 端点（共享）
│           └── ...
├── services/                # 服务代理层
│   ├── agent_service_proxy.py
│   ├── chat_service_proxy.py
│   └── ...
├── core/
│   └── config.py            # 配置（复用主应用）
└── static/
    └── evaluation/          # Evaluation 前端构建产物
```

## 与主应用的区别

1. **端口**: IntyEval 默认运行在 8001 端口，主应用在 8000 端口
2. **功能范围**: IntyEval 专注于内部运营工具，不包含用户面向的功能
3. **前端服务**: IntyEval 只服务 evaluation 前端，主应用不包含前端服务

## 开发注意事项

1. **导入路径**: IntyEval 需要能够导入 `app/` 目录下的模块
2. **数据库连接**: 确保两个应用使用相同的数据库配置
3. **认证 Token**: 两个应用使用相同的 JWT 密钥，token 可以跨应用使用
4. **CORS 配置**: IntyEval 可能需要不同的 CORS 配置

## 构建 Evaluation 前端

Evaluation 前端构建产物会输出到 `eval_app/static/evaluation/`：

```bash
cd evaluation
./build.sh
```

构建脚本会自动将产物复制到正确的位置。

