# InTy Backend Developer Guide

InTy is a FastAPI- and PostgreSQL-based AI chat backend that integrates LangChain and LangGraph for managing multi-model AI agents in an asynchronous architecture. The project supports features such as user authentication, subscription management, and AI voice services.

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

| Layer | Key Modules | Notes |
|-------|-------------|-------|
| **Entry point** | [`app/main.py`](app/main.py) | Configures FastAPI, CORS, error handlers, and startup tasks (e.g., agent initialization, Keep Talking service) |
| **API layer** | [`app/api/v1`](app/api/v1) | Router modules for agents, chats, auth, subscriptions, etc. provide REST endpoints |
| **Configuration** | [`app/core/config.py`](app/core/config.py) | Settings defined with dataclasses and loaded from `config.yaml` via `load_config` |
| **Models** | [`app/models`](app/models) | SQLAlchemy models (e.g., `User`) map database tables and relationships |
| **Schemas** | [`app/schemas`](app/schemas) | Pydantic models validate request/response data (mirroring model structure) |
| **Services** | [`app/services`](app/services) | Business logic; for example, `chat_service.py` manages chat sessions and caching logic |
| **Agent engine** | [`app/core/agent`](app/core/agent) | LangChain/LangGraph-based agent system with custom state, memory tools, and model configuration utilities |
| **Documentation** | [`docs/`](docs) | Design notes for character cards, AI voice, prompt templates, Google Play subscriptions, etc. |
| **Migrations** | [`alembic/`](alembic) | Database schema migrations |
| **Utilities** | [`scripts/`](scripts) | Setup helpers and maintenance scripts |
| **Testing** | [`testing/`](testing) | Sample data and test utilities |

## Important Concepts

- **Config-driven setup** – [`config.yaml`](config.yaml.example) controls database credentials, Google OAuth, agent defaults, voice generation, and other services; see the [README](README.md) for environment prerequisites.
- **Asynchronous I/O** – Database access and most services use `AsyncSession` and `async def` for concurrency.
- **Agent lifecycle** – [`app/core/agent/agent.py`](app/core/agent/agent.py) shows how agents use LangChain, Postgres message history, and custom tools.
- **Service layer** – Core logic (e.g., chat creation, caching, subscriptions) is separated from API endpoints for easier reuse and testing.

## Next Steps for New Contributors

1. **Run locally**: Follow the setup and launch instructions in the [README](README.md) to spin up PostgreSQL, apply migrations, and start the FastAPI server.
2. **Review docs**: Browse the [`docs/`](docs) folder for deeper dives into the AI voice system, prompt templates, and subscription flows.
3. **Explore agents**: Study the [`app/core/agent`](app/core/agent) modules to understand the LangGraph agent architecture and memory tools.
4. **Inspect services**: Look at modules under [`app/services`](app/services) to see how business logic, caching, and external APIs (Google Cloud Storage, ElevenLabs, etc.) are implemented.
5. **Check tests**: Examine the test files in the repository to see example usage patterns and expected behaviors.

This guide provides a map of where features live and how the system pieces fit together. The docs and service implementations are good resources for understanding specialized components such as character cards, AI voice, or subscription management.
