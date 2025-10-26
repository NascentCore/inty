# app

## Tips

```bash
# 进入交互环境，只需要 mount config.yaml 即可
docker run --volume /opt/inty-pre-prod/config.yaml:/config.yaml -it ghcr.io/nascentcore/inty-backend/inty-server:<tag> bash
```

## Stainless OpenAPI generator

```bash
brew install stainless-api/tap/stl
stl auth login
stl init
```

- <https://app.stainless.com/inty/inty/overview> Stainless OpenAPI SDK generation project.

[Stainless core concepts](https://www.stainless.com/docs/guides/configure#core-concepts)

- Methods are invoked for actual APIs [defined in YAML](stainless.yml)
- Models are types reused throughout the SDKs
- Resources are a collection actual artifacts used in Client code.

There are 3 phases on Stainless:

1. Generate SDK, pushed to Stainless' internal github repo
2. Push to our own repo from Stainless' internal github repo
3. [Do not use] Push to language specific registry (pip/npm/maven)

<img width="800" height="1150" alt="image" src="https://github.com/user-attachments/assets/8c9c6098-921f-4c7e-a409-bc460805424c" />

You can trigger build on stainless.com by uploading your new openapi.json
to Stainless studio.

Or using stl cli with stainless.yml matches stainless studio's configs.

### Typescript

### Kotlin

## Deployment

- Run [build_and_deploy.yml](../.github/workflows/build_and_deploy.yml)
  to deploy the app to production server
- Open Google Cloud Console, login with `it@sxwl.ai` (or your own account)
- Open Compute Engine, and find `dev-intance`
- `/etc/nginx/conf.d/sxwl.ai.conf` has the host's nginx config

- Launch postgres with pgvector extensions

```bash
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
```

- If alembic shows multiple heads error, you can delete the heads shown by `alembic show heads`

- Install alembic and update database `alembic upgrade head`

## Cursor Summary

- Framework: FastAPI 应用（`app/main.py`），路由分层于 `app/api/v1` 与 `app/api/v2`（用户、聊天、代理、资源、设置、鉴权、订阅、语音、评测、通知、管理等）。
- Data: SQLAlchemy 模型位于 `app/models`；数据库会话/基类在 `app/db`；迁移由仓库根目录 `alembic/` 管理。
- Schemas: Pydantic 架构体在 `app/schemas`，与路由/服务之间进行 IO 验证与转换。
- Services: 领域服务集中于 `app/services`（例如 `chat_service`、`agent_service`、`subscription_service`、`voice_service`、`evaluation_service` 等）。
- LLM/AI: 提供方与辅助封装在 `app/utils`（`openai_client.py`、`gemini.py`、`langchain.py` 等），供服务层调用。
- Prompting: 角色/人格/语气等提示词素材在 `app/core/agent` 与 `app/core/prompting`。
- Voice: 语音/TTS 相关模型与工具在 `app/core/voice`。
- Config/Logging: 集中配置与日志在 `app/core/config.py`、`app/core/logging.py`。
- Middleware: 错误处理中间件见 `app/middleware/error_handler.py`。
- OpenAPI/SDK: `app/openapi.json` 与仓库根部 `stainless.yml` 协同 Stainless 生成多语言 SDK（详见本 README 前半部分说明）。
