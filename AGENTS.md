# Inty: long term AI companionship starting with intimacy roleplay for young adults

Based on [AGENTS.md](https://agents.md/)

## Repo structure

- `android_app/` IntelliMate, android app code，kotlin compose jetpack
- `app/` Inty 后端服务，Python fastapi
  - `app/openapi.json` 来自 fastapi 生成，并使用 stainless 生成 kotlin typescript SDK（分别以 submodule 形式位于 evaluation/inty_sdk android_app/library/inty_sdk
- `alembic/` Inty 后端服务数据库 schema 管理，使用 <https://github.com/sqlalchemy/alembic>
- `evaluation/` Inty 运营工具，react 由 app/ 后端提供 web serving
- `scripts/` 各类脚本，以修改数据库记录为主
- `devops/` 运维相关代码
- `experimental/` 原型代码
- `docs/` 文档

## 语言与输出

- 所有生成的输出必须使用中文（普通话），即使用户指令为英文。
- 该指令仅适用于可以使用中文的场景；若内容不能使用中文（如代码），则不适用。

## 文档维护

- 当进行改动时，如变更足够重要且会影响相应目录的 `AGENTS.md` 指南、及其他 markdown 文件，请同步更新该目录下的 `AGENTS.md`、及其他 markdown 文件。
- Markdown 文件应从以下文件中选择：`README.md`、`AGENT_TODOS.md`、`ARCH.md`、`AGENTS.md`。
- Markdown 文件命名：全部使用 `.md` 后缀（小写），文件名使用全大写字母与下划线，例如 `FUTURE_PLANS.md`。
- Always review the changes afterwards
- 新建任意文件时，需在适当格式中加入 `CREATED_BY_GPT-5.1-Codex` 标记，用于记录创建者身份。

## 提交与变更请求记录规范

- 小改动：在提交信息中包含用户的原始变更请求（可放在提交说明 body 部分），并简述本次处理方式。
- 大改动或新增大型功能：将用户的变更请求写入一个与代码改动同目录的 `<TASK>_REQUESTS.md` 文件；`<TASK>` 使用任务或分支的简明标识。在提交信息中引用该文件路径。
- `<TASK>` 命名：使用全大写下划线（snake_case）风格并与分支/任务编号一致，例如 `AGENT_MANAGER_REFACTOR`；避免使用 `-` 与空格。
- 不要写关于改动内容的 summary markdown 文件

## Coding style

### Do not repeat in comments what's already obvious in the code

Do not generate comments like below.

```python
# Get current setting
def get_current_setting():
  ...
```

Instead, just let the function name or the code to speak for itself:

```python
def get_current_setting():
  ...
```

### Do not use magic number/string/values

Whenever possible define constants to name magic number/string/values to aid code readability.

### Prefer early return

Prefer:

```python
if false:
  return None

...
```

Over

```python
if true:
  ...
else:
  return None
```

## Python

- 避免使用 `try ... except Exception` 来覆盖所有异常，而应该至拦截函数能处理的异常
- 测试用例目录不应被声明为包：包含 `test_*.py` 的测试目录不要放置 `__init__.py`；但用于复用的测试辅助库目录应当作为包存在，并包含 `__init__.py`。
- 所有正式 Python 包必须包含空的 `__init__.py`（仅用于声明包）。

## Android App

- 只支持 portrait 显示；不支持 landscape 显示，无需在改动时考虑兼容 landscape 显示。

## CloudFlare

- @<https://developers.cloudflare.com/llms.txt>
- @<https://developers.cloudflare.com/workers/prompt.txt>
- @<https://developers.cloudflare.com/stream/llms-full.txt>
- @<https://developers.cloudflare.com/developer-platform/llms-full.txt>

来自官方文档链接 https://developers.cloudflare.com/stream/changelog/

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
- OpenRouter 模型：仅超级用户获取模型列表以供评测使用
- 订阅/用量限制：创建 Agent、文生图、语音生成均接入限额检查与用量记录

## 提示词与角色卡集成

- 支持 SillyTavern V2：字段映射到 Agent 模型，优先级为“角色卡字段 > legacy prompt”。
- 提示词层次：系统提示词 > 角色卡上下文（`personality`/`scenario`/`message_example`）> 用户信息 > 聊天历史。
- premium 模式：根据 `chat_settings.premium_mode` 选择不同的模式提示词。

## Extensions 扩展字段

- 统一扩展容器：`agents.extensions`（JSON），前端/后端约定键值结构。
- 头像裁切：`extensions.avatar_crop` 提供裁切坐标，后端序列化时基于 `background` 生成裁切头像 URL。
- 缓存策略：Agent 轻量配置含 `extensions` 缓存 30 分钟；更新后主动失效并触发 AgentManager 重载。

## 图片与资源

- URL 归一化：写库前将 CDN URL 归一化为 GCS 存储路径；读取时按终端类型转换回 CDN。
- 资源尺寸：`resources` 表存储图片尺寸，响应中补齐 `avatar_size`、`background_size`。

## 语音系统

- 提供商：以 ElevenLabs 为主（可扩展）；创建/更新 Agent 后异步生成 `opening` 的语音并写入 `opening_audio_url`。
- 文本清洗：生成前移除心理/动作描写；支持缓存命中、GCS 存储与用量记录。
- 默认音色：可基于 Agent 性别选择默认 `voice_id`，也可在 Agent 层显式指定。

## 推荐与排序

- 支持创建时间、确定性随机（基于 `sort_seed`）、基于评分的平衡随机（`score*2 + hash(seed)%100`）等策略，支持分页。

## 缓存与重载

- AgentData 缓存：聊天轻量数据缓存 30 分钟；更新后失效。
- AgentManager：实例缓存、闲置清理、强制重载，保证提示词/配置即时生效。

## 评测前端（evaluation）对接

- 前端通过上述接口管理 Agent/模型并发起评测；UI 支持头像裁切显示与语音试听。

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
