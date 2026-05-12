# Inty backend servers

## 双应用说明

| 应用 | 入口模块 | 典型部署 | `/api/v1` 来源 |
|------|----------|----------|----------------|
| **Inty**（主后端，Android） | `backend/inty/main.py` | App 对应后端 | `app.api.v1.router.api_router` |
| **Ops**（运营 / evaluation） | `backend/ops/main.py` | ops.inty.cc、dev.ops.inty.cc | `shared_router`（`backend/ops/api/v1/shared.py`）+ `backend/ops/api/v1/evaluation.py` + `backend/ops/api/v1/festival_memory.py` |

## 本地服务启动

- 首次运行前启动数据库依赖：`docker compose up pgvector -d`
- 启动后端服务：`./backend/inty/start.sh --dev`
- 启动推送服务：`./backend/push_worker/start.sh`
- 本地服务启动成功后，可通过 `https://localhost:8000/` 访问并供测试调用
- **Ops 平台**（evaluation）：`./backend/ops/start.sh --dev`，默认 `http://localhost:8001`；生产部署见 ops.inty.cc、dev.ops.inty.cc（Cloud Run 或同 VM nginx 反代）

## Agent 架构概览

- 核心对象：`Agent` 负责提示词组装与模型调用；`AgentManager` 负责实例缓存、并发安全、闲置清理与重载。
- 模型配置优先级：优先读取 `settings.llm_config`，缺失字段回落到全局配置；所有缺失值以全局默认补齐。
- 提示词分层：主提示词（main）、模式提示词（mode，含 premium 切换）、输出格式提示词（output_format），并在必要时强制使用全局默认。
- 会话历史：使用 `chat_history` 表配合 `PostgresChatMessageHistory`；支持相关历史裁剪以控制上下文长度。
- 客户端复用：OpenAI 客户端封装了 LangSmith 追踪并做实例级缓存，避免频繁创建客户端。

## 数据模型与 Schema

- SQLAlchemy 模型 `app/models/agent.py`：新增/重点字段
  - 提示词：`main_prompt`, `mode_prompt`
  - 角色卡：`personality`, `scenario`, `message_example`, `creator_notes`, `tags`, `character_version`, `extensions`
  - 语音：`opening_audio_url`
- Pydantic 模型 `app/schemas/agent.py`：
  - 模型配置：`llm_config`（落入 `settings.llm_config` 持久化）
  - 字段序列化：`intro`/`opening` 支持 `{{ char }}`/`{{ user }}` 变量渲染；图片 URL 与尺寸透传资源表信息
- 兼容：`prompt` 字段已废弃，创建/更新时自动迁移到 `personality`；`readable_id` 保留但不再展示。

## API 能力（/api/v1/ai/agents）

- 列表/搜索/推荐/关注：`GET /me`、`GET /search`、`GET /recommend`、`POST|DELETE /{agent_id}/follow`
- 详情/创建/更新/删除：`GET /{agent_id}`、`POST /`、`PUT /{agent_id}`、`DELETE /{agent_id}`
- 角色卡：导入（JSON/文件）、导出、校验、功能列表
- OpenRouter 模型：仅超级用户可访问 `GET /api/v1/ai/agents/models/openrouter`；当实时拉取失败时由 `app/services/scoring_service.py` 提供包含 `Claude 3.5 Sonnet` / `Claude 3.5 Haiku` 等模型的兜底列表，evaluation 前端的 `services/api.ts` 与 `services/modelCache.ts` 需保持完全同步。
- 订阅/用量限制：创建 Agent、文生图、语音生成均接入限额检查与用量记录

## 提示词与角色卡集成

- 支持 SillyTavern V2：字段映射到 Agent 模型，优先级为“角色卡字段 > legacy prompt”。
- 提示词层次：系统提示词 > 角色卡上下文（`personality`/`scenario`/`message_example`）> 用户信息 > 聊天历史。
- premium 模式：根据 `chat_settings.premium_mode` 选择不同的模式提示词。

## Extensions 扩展字段

- 统一扩展容器：`agents.extensions`（JSON），前端/后端约定键值结构。
- 头像裁切：`extensions.avatar_crop` 提供裁切坐标，后端序列化时基于 `background` 生成裁切头像 URL。
- 缓存策略：Agent 轻量配置含 `extensions`，TTL 见 `agent.agent_config_cache_ttl_seconds`（默认 20 分钟）；更新后主动失效并触发 AgentManager 重载。

## 图片与资源

- URL 归一化：写库前将 CDN URL 归一化为 GCS 存储路径；读取时按终端类型转换回 CDN。
- 资源尺寸：`resources` 表存储图片尺寸，响应中补齐 `avatar_size`、`background_size`。

## 语音系统

- 提供商：以 ElevenLabs 为主（可扩展）；创建/更新 Agent 后异步生成 `opening` 的语音并写入 `opening_audio_url`。
- 文本清洗：生成前移除心理/动作描写；支持缓存命中、GCS 存储与用量记录。
- 默认音色：可基于 Agent 性别选择默认 `voice_id`，也可在 Agent 层显式指定。
- 电话通话：`/api/v1/phone-calls/*` 用 Twilio PSTN + Media Streams 桥接现有 Gemini Live；聊天中当前轮显式 `Call me at ...` 可触发外呼，直接来电用 HMAC caller binding 识别用户，不写入 `users.phone`。

## 推荐与排序

- 支持创建时间、确定性随机（基于 `sort_seed`）、基于评分的平衡随机（`score*2 + hash(seed)%100`）等策略，支持分页。

## 缓存与重载

- AgentData 缓存：聊天轻量数据（含 voice_id）由 `agent.agent_config_cache_ttl_seconds` 控制 TTL，默认 20 分钟；更新后主动失效。短 TTL 便于 ops 与后端分离部署时（ops 直写 DB）一段时间内读到最新数据。
- AgentManager：实例缓存、闲置清理、强制重载，保证提示词/配置即时生效。

## 评测前端（evaluation）对接

- 前端通过上述接口管理 Agent/模型并发起评测；UI 支持头像裁切显示与语音试听。
- Claude 模型说明集中在 `evaluation/AGENTS.md`，涉及的兜底列表、缓存与测试基线需与本文件保持一致。

## Claude 模型与评测

- 默认评分模型列表定义于 `app/services/scoring_service.py`，并由 `app/api/v1/endpoints/agents.py` 的 OpenRouter 接口、`evaluation/services/api.ts` 的 5 秒超时 fallback 以及 `evaluation/services/modelCache.ts` 的缓存兜底共同复用；列表中包含 `anthropic/claude-3.5-sonnet`、`anthropic/claude-3.5-haiku`（context length 200k）等最新 Claude 版本。
- 如需新增或替换 Claude 型号，需同时更新上述四处代码与依赖这些常量的测试（`tests/app/services/test_agent_service.py`、`evaluation/test_integration.py` 等），并在文档中记录变更。
- 评测 UI 的模型下拉依赖浏览器 `localStorage`（键前缀 `inty_scoring_models_*`）；调试 Claude 列表时请调用 `modelCacheService.clearScoringCache()` 或手动清除缓存以避免看到过期数据。
- 超级用户可通过 `GET /api/v1/ai/agents/models/openrouter` 查看 OpenRouter 实时模型；若调用失败，后端会回退到默认列表以保证评测流程不中断。

## 配置与性能

- 关键配置：`agent/database/gcs/elevenlabs` 段落影响实例池、连接池、上传与生成能力。
- 性能要点：客户端复用、实例缓存、轻量查询与缓存、历史裁剪、分页与确定性随机、资源/语音缓存。

## 安全/风控与兼容

- RAI：图像生成功能对过滤结果进行说明并尽量返回原因。
- 兼容：保留 legacy 字段迁移逻辑；用户信息同步读取路径已标记废弃，规划迁移到独立用户服务。

## 术语

- Agent/角色、角色卡（Character Card）、系统/角色/聊天提示词、记忆（Memory）、Extensions、开场白（opening）。

## 关联文档

- `docs/AGENT_CHARACTER_CARD_INTEGRATION.md`
- `docs/CHARACTER_CARD_SYSTEM.md`
- `docs/AGENT_EXTENSIONS_SYSTEM.md`
- `docs/AI_VOICE_SYSTEM.md`
