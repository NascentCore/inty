# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

InTy is a FastAPI-based AI chat application backend that integrates LangChain, LangGraph, and supports multiple AI models. It provides a complete AI conversation solution with subscription services and intelligent agent management.

## Development Commands

### Start Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Operations
```bash
# Create database migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Initialize subscription plans
python scripts/init_subscription_plans.py
```

### Testing
```bash
# Run tests
pytest

# Run specific test
pytest test_pagination.py
```

### Code Quality
```bash
# Format code
black app/

# Sort imports
isort app/
```

## Architecture

### Core Components

**App Structure:**
- `app/main.py` - Application entry point with FastAPI setup, CORS, error handlers
- `app/api/v1/` - API routes organized by feature (agents, auth, chats, subscription, etc.)
- `app/core/` - Core system components including AI agent engine, config, security
- `app/services/` - Business logic layer with services for each domain
- `app/models/` - SQLAlchemy database models
- `app/schemas/` - Pydantic validation schemas

**AI Agent System:**
- Built on LangGraph for complex conversation flows and state management
- `app/core/agent/agent.py` - Main agent engine with memory integration
- `app/core/agent/memory.py` - Memory system using PostgreSQL + pgvector
- `app/core/agent/prompt_template.py` - Template system for dynamic prompts
- Supports multiple AI models (OpenAI, Anthropic, Google AI)
- Agent instances are cached and managed by `AgentManager` class

**Database:**
- PostgreSQL with async SQLAlchemy ORM
- Alembic for database migrations
- Key tables: users, agents, chats, messages, subscription_plans, user_subscriptions
- pgvector extension for vector embeddings

**Authentication:**
- JWT token-based authentication
- Multiple auth methods: phone, Google OAuth, guest mode
- Firebase integration for identity services

**Subscription System:**
- Google Play subscription integration
- Subscription plans with usage tracking
- Receipt validation and purchase verification

### Key Services

**Agent Service (`app/services/agent_service.py`):**
- Manages AI agent CRUD operations
- Handles agent publishing and recommendations

**Chat Service (`app/services/chat_service.py`):**
- Manages chat sessions and messages
- Integrates with agent system for responses

**Keep Talking Service (`app/services/keep_talking_service.py`):**
- Automatically continues conversations based on time and context
- Monitors idle sessions and generates follow-up messages

**Subscription Service (`app/services/subscription_service.py`):**
- Handles Google Play subscription lifecycle
- Manages subscription features and usage limits

### Configuration

The application uses YAML configuration (`config.yaml`) with sections for:
- App settings (debug, CORS origins)
- Database connection
- AI model configurations
- Google services (OAuth, Play Store, Cloud Storage)
- Security settings (JWT secret, algorithm)
- Keep Talking service settings

## Development Notes

### Agent System
- Agent instances are cached in memory with automatic cleanup
- Each agent has its own thread pool for concurrent chat processing
- Memory system uses LangMem with PostgreSQL backend for persistent conversation history
- User context is automatically injected into conversations

### Database Patterns
- Uses async SQLAlchemy with proper session management
- Connection pooling configured for performance
- Migrations are version-controlled in `alembic/versions/`

### Error Handling
- Centralized error handlers in `app/middleware/error_handler.py`
- Proper exception handling for JWT, validation, and database errors

### Logging
- Uses Loguru for structured logging
- Configurable log levels and file rotation
- Debug mode can save full conversation messages to database

### Testing
- Pytest framework available
- Test pagination example in `test_pagination.py`

## Common Development Patterns

### Creating New Endpoints
1. Add route to appropriate file in `app/api/v1/endpoints/`
2. Create corresponding service method in `app/services/`
3. Add Pydantic schemas in `app/schemas/`
4. Update database models if needed

### Working with Agents
- Use `agent_manager.get_agent()` to get cached agent instances
- Agent configuration includes model settings and prompts
- Memory tools are automatically available to agents

### Subscription Features
- Check user subscription status before allowing premium features
- Use `subscription_service` for all subscription-related operations
- Track usage for billing purposes

## Key Files to Understand

- `app/main.py` - Application setup and lifecycle
- `app/core/agent/agent.py` - AI agent implementation
- `app/core/config.py` - Configuration management
- `app/services/keep_talking_service.py` - Conversation continuation logic
- `app/api/v1/endpoints/chats.py` - Chat API implementation