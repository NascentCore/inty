# InTy 后端开发人员指南

InTy 是一个基于 FastAPI 和 PostgreSQL 的 AI 聊天后端，集成了 LangChain 和 LangGraph，用于在异步架构中管理多模型 AI 代理。 project支持用户认证、订阅管理、AI语音服务等功能。## 代码标准格式```bash
brew install ktfmt
pip install black
npm install --save-dev --save-exact prettier
# 使用标准脚本格式化所有代码
./fmt.sh
```## 启动本地本地服务

- 配置.yaml
- GCP 服务帐户 json
- gcp dev web 客户端 ID 令牌

## Gemini CLI、Claude Code、Cursor 的常用指令

- 在每个写入的文件的底部添加一个空行。## __保留__4__

当更改现有表，或添加新表，或删除表时，
你必须跑`alembic revision --autogenerate -m "description"`生成新的 alembic 版本。添加新表时，还需要导入表`app/models/__init__.py`这样 alembic 就可以获取表定义。部署后端服务时，还需要运行`alembic upgrade head`将数据库同步到代码库。所有表定义必须添加到`app/models`目录以保持一致性。## 核心结构

|层|关键模块|笔记|
| ----------------- | ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| **入口点** | [`app/main.py`](应用程序/main.py) |配置 FastAPI、CORS、错误处理程序和启动任务（例如、代理初始化、Keep Talking 服务） |
| **__保留__14__层** | [`app/api/v1`](应用程序/api/v1) |用于代理、聊天、身份验证、订阅等的路由器模块。pr提供 REST 端点 |
| **配置** | [`app/core/config.py`](应用程序/核心/配置。py）|使用数据类定义并加载的设置`config.yaml` via `load_config`|
| **型号** | [`app/models`]（应用程序/模型）| SQLAlchemy 模型（例如,`User`) 映射数据库表和关系 |
| **架构** | [`app/schemas`]（应用程序/架构）| Pydantic 模型验证请求/响应数据（镜像模型结构）|
| **服务** | [`app/services`]（应用程序/服务）|业务逻辑；例如，`chat_service.py`管理聊天会话和缓存逻辑|
| **代理引擎** | [`app/core/agent`]（应用程序/核心/代理）|基于 LangChain/LangGraph 的代理系统，具有自定义状态、内存工具和模型配置实用程序 |
| **文档** | [`docs/`]（文档）|人物卡、AI语音、prompt模板、Google Play订阅等的设计笔记。|
| **迁移** | [`alembic/`](__保留__10__) |数据库架构迁移 |
| **公用事业** | [`scripts/`]（脚本）|设置帮助程序和维护脚本 |
| **测试** | [`testing/`]（测试）|样本数据和测试实用程序 |

## 配置光标

### 使用黑色格式化程序启用保存格式

目标：安装并启用黑色格式化程序以在保存时格式化文件，使用默认的黑色格式样式。

- 首先安装黑色格式化程序

  <img width="600" alt="image" src="https://github.com/user-attachments/assets/279a14ae-1814-4f89-b82b-0215810e3624" />

- 然后启用“保存时格式化”

  <img width="600" alt="image" src="https://github.com/user-attachments/assets/aad4af61-bb27-4b4d-9ebe-5c4bb57316b1" />
  <img width="600" alt="image" src="https://github.com/user-attachments/assets/aa251443-ada9-4331-9c99-1756aed57344" />

结果：每当您对文件进行更改时，文件就会被格式化。