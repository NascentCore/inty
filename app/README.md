＃ 应用程序

＃＃ 尖端```bash
# 进入交互环境，只需要 mount config.yaml 即可
docker run --volume /opt/inty-pre-prod/config.yaml:/config.yaml -it ghcr.io/nascentcore/inty-backend/inty-server:<tag> bash
```## 不锈钢OpenAPI 发电机```bash
brew install stainless-api/tap/stl
stl auth login
stl init
```- <https://app.stainless.com/inty/inty/overview> 不锈钢 OpenAPI SDK 代 project。

[不锈钢核心概念](https://www.stainless.com/docs/guides/configure#core-concepts)

- 为实际的 APIs [在 YAML 中定义](stainless.yml) 调用方法
- 模型是在 SDK 中重复使用的类型
- 资源是客户端代码中使用的实际工件的集合。

不锈钢有3个阶段：

1.生成SDK，推送到Stainless的内部github仓库
2.从Stainless的内部github仓库推送到我们自己的仓库
3. [不要使用] 推送到特定于语言的注册表 (pip/npm/maven)

<img width="800" height="1150" alt="image" src="https://github.com/user-attachments/assets/8c9c6098-921f-4c7e-a409-bc460805424c" />您可以通过上传新的 openapi.json 来触发不锈钢网站上的构建
到不锈钢工作室。

或者使用 stl cli 和不锈钢.yml 匹配不锈钢工作室的配置。

### 打字稿

### 科特林

## 部署

- 运行 [build_and_deploy.yml](../.github/workflows/build_and_deploy.yml)
  将应用程序部署到 prduction 服务器
- 打开 Google Cloud Console，登录`it@sxwl.ai`（或您自己的帐户）
- 打开计算引擎，然后找到`dev-intance`
- `/etc/nginx/conf.d/sxwl.ai.conf`有主机的 nginx 配置

- 启动带有 pgvector 扩展的 postgres```bash
docker run --name dev-postgres \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -p 5432:5432 \
    -d pgvector/pgvector:pg16

# Login with psql
psql -h localhost -U postgres
> \l # List all databses
> DROP DATABASE <db>; # Drop database
# Drop all connections to the database
> SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'inty_prd'
  AND pg_stat_activity.pid <> pg_backend_pid();

createdb -h localhost -U postgres inty_prd
alembic upgrade head
```- 如果alembic显示多头错误，您可以删除显示的头`alembic show heads`- 安装alembic并更新数据库`alembic upgrade head`## 光标摘要

- 框架：FastAPI应用（`app/main.py`），路由分层于 `app/api/v1` 与 `app/api/v2`（用户聊天、代理、资源、设置、鉴权、订阅、语音、体育、通知、管理等）。
- 数据：SQLAlchemy 模型位于`app/models`；数据库会话/基类在 `app/db`；迁移由仓库根目录 `alembic/`管理。
- 架构：Pydantic 架构体在`app/schemas`，与路由/服务之间进行IO验证与转换。
- Services: 领域服务集中于`app/services`（例如 `chat_service`、`agent_service`、`subscription_service`、`voice_service`、`evaluation_service`等）。
- LLM/AI：提供方与辅助封装`app/utils`（`openai_client.py`、`gemini.py`、`langchain.py`等），提供服务层调用。
- Prompting: 角色/性格/语气等提示词素材在`app/core/agent` 与 `app/core/prompting`。
- 语音：语音/TTS 相关模型与工具`app/core/voice`。
- 配置/日志记录：集中配置与日志在`app/core/config.py`、`app/core/logging.py`。
- 中间件：错误处理中间件见`app/middleware/error_handler.py`。
- OpenAPI/SDK：`app/openapi.json` 与仓库根部 `stainless.yml`不锈钢生成多语言SDK（参见本README前半部分说明）。