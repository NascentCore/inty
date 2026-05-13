# InTy Backend Developer Guide

InTy is a FastAPI- and PostgreSQL-based AI chat backend that integrates LangChain and LangGraph for managing multi-model AI agents in an asynchronous architecture. The project supports features such as user authentication, subscription management, and AI voice services.

## 代码标准格式

```bash
brew install ktfmt
pip install black
npm install --save-dev --save-exact prettier
# 使用标准脚本格式化所有代码
./tools/scripts/fmt.sh
# 说明：tools/scripts/fmt.sh 会自动调用 prettier 处理 JSON/Markdown/JS/TS/HTML/CSS 等文本文件，并且已经支持 YAML（.yaml/.yml）文件的格式化。
```

## 启动本地后端服务

- config.yaml
- gcp service account json
- gcp dev web client id token

## Common instructions for Gemini CLI, Claude Code, Cursor

- Add a blank line at the bottom of each and every file written.

## Alembic

When change existing tables, or add new tables, or removing tables,
you must run `alembic revision --autogenerate -m "description"`
to generate new alembic versions.

When adding new tables, you also need to import the table in
`app/models/__init__.py` so that alembic can pick up the table definition.

When deploying backend service, you also need to run `alembic upgrade head`
to sync the db to the codebase.

All table definitions must be added to `app/models` directory for consistency.

## Core Structure

| Layer             | Key Modules                                | Notes                                                                                                          |
| ----------------- | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| **Entry point**   | [`backend/inty/main.py`](../inty/main.py)        | Configures FastAPI, CORS, error handlers, and startup tasks (e.g., agent initialization, Keep Talking service) |
| **API layer**     | [`app/api/v1`](../../app/api/v1)                 | Router modules for agents, chats, auth, subscriptions, etc. provide REST endpoints                             |
| **Configuration** | [`app/core/config.py`](../../app/core/config.py) | Settings defined with dataclasses and loaded from `config.yaml` via `load_config`                              |
| **Models**        | [`app/models`](../../app/models)                 | SQLAlchemy models (e.g., `User`) map database tables and relationships                                         |
| **Schemas**       | [`app/schemas`](../../app/schemas)               | Pydantic models validate request/response data (mirroring model structure)                                     |
| **Services**      | [`app/services`](../../app/services)             | Business logic; for example, `chat_service.py` manages chat sessions and caching logic                         |
| **Agent engine**  | [`app/core/agent`](../../app/core/agent)         | LangChain/LangGraph-based agent system with custom state, memory tools, and model configuration utilities      |
| **Documentation** | [`docs/`](../docs)                            | Design notes for character cards, AI voice, prompt templates, Google Play subscriptions, etc.                  |
| **Migrations**    | [`alembic/`](../../alembic)                      | Database schema migrations                                                                                     |
| **Utilities**     | [`tools/scripts/`](../../tools/scripts)                      | Setup helpers and maintenance scripts                                                                          |
| **Testing**       | [`testing/`](testing)                      | Sample data and test utilities                                                                                 |

## Configuring Cursor

### Enable format on save with black formatter

Goal: install and enable black formatter to format file on save, use the default black format style.

- First install Black Formatter

  <img width="600" alt="image" src="https://github.com/user-attachments/assets/279a14ae-1814-4f89-b82b-0215810e3624" />

- Then enable "format on save"

  <img width="600" alt="image" src="https://github.com/user-attachments/assets/aad4af61-bb27-4b4d-9ebe-5c4bb57316b1" />
  <img width="600" alt="image" src="https://github.com/user-attachments/assets/aa251443-ada9-4331-9c99-1756aed57344" />

Result: file got formated whenever you make a change to the file.
