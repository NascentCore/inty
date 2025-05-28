# InTy Backend

InTy 的后端服务，基于 FastAPI 和 PostgreSQL 构建的 AI 聊天应用后端。

## 功能特性

- 用户认证
  - 手机号登录
  - Google OAuth 登录
  - 游客模式
  - JWT 令牌认证
- AI 角色管理
  - 创建和管理 AI 角色
  - 角色关注功能
  - 角色可见性控制
  - 角色状态管理（待审核、已批准、已拒绝）
- 聊天功能
  - 实时消息发送和接收
  - 支持文本、语音、图片消息
  - 聊天设置管理
  - 多语言支持
- 用户设置
  - 语言偏好
  - 语音开关
  - 持续对话设置
- 资源管理
  - 图片上传和管理
  - 语音文件处理
  - 用户头像管理

## 技术栈

- Python 3.8+
- FastAPI - 高性能 Web 框架
- PostgreSQL - 关系型数据库
- SQLAlchemy - ORM 框架
- Alembic - 数据库迁移工具
- JWT - 用户认证
- Google OAuth - 第三方登录
- Pydantic - 数据验证
- Python-dotenv - 环境变量管理

## 数据库结构

- users - 用户信息表
- agents - AI 角色表
- messages - 聊天消息表
- chat_settings - 聊天设置表
- agent_followers - 角色关注关系表
- settings - 用户设置表

## 开发环境设置

1. 克隆项目
```bash
git clone https://github.com/NascentCore/inty-backend.git
cd inty-backend
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，设置必要的环境变量：
# - 数据库连接信息
# - JWT 密钥
# - Google OAuth 配置
# - 其他应用设置
```

5. 初始化数据库
```bash
# 创建数据库
createdb inty_db

# 运行数据库迁移
alembic upgrade head
```

6. 运行开发服务器
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务器将在 http://localhost:8000 运行

## API 文档

启动服务器后，可以访问以下地址查看 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 项目结构

```
inty-backend/
├── alembic/              # 数据库迁移文件
├── app/
│   ├── api/             # API 路由
│   ├── core/            # 核心配置
│   ├── models/          # 数据库模型
│   ├── schemas/         # Pydantic 模型
│   ├── services/        # 业务逻辑
│   └── main.py          # 应用入口
├── tests/               # 测试文件
├── .env                 # 环境变量
├── .env.example         # 环境变量示例
├── alembic.ini          # Alembic 配置
├── requirements.txt     # 项目依赖
└── README.md           # 项目文档
```

## 测试

运行测试：
```bash
pytest
```

## 部署

1. 设置生产环境变量
2. 使用 gunicorn 运行：
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```