# Inty：长期的人工智能陪伴从年轻人的亲密角色扮演开始

基于[代理。md](https://agents.md/)

## 回购结构

-`android_app/`IntelliMate，android 应用程序代码，kotlin compose jetpack
-`app/`Inty 云端服务，Python fastapi
  -`app/openapi.json`来自 fastapi 生成，并使用不锈钢生成 kotlin typescript SDK（以各自子模块形式位于evaluation/inty_sdk android_app/library/inty_sdk
-`alembic/`Inty 云端服务数据库模式管理，使用 <https://github.com/sqlalchemy/alembic>
-`evaluation/`Inty 运营工具，由 app/ 监听提供网络服务
-`experimental/` 原型代码
- `scripts/` 各类脚本，以修改数据库记录为主
- `devops/` 运维相关代码
- `docs/` 文档

## 语言与输出

- 所有生成的输出必须使用中文（普通话），即使用户指令为英文。
- 该指令仅适用于可以使用中文的场景；若内容不能使用中文（如代码），则不适用。

## 文档维护

- 当进行改动时，如变更足够重要且会影响相应目录的 `AGENTS.md`指南、及其他markdown文件，请同步更新该目录下的`AGENTS.md`、及其他markdown文件。
- Markdown 文件应从以下文件中选择：`README.md`、`AGENT_TODOS.md`、`ARCH.md`、`AGENTS.md`。
- Markdown 文件命名：全部使用`.md` 后缀（小写），文件名使用全大写字母与下划线，例如 `FUTURE_PLANS.md`。

## 提交与变更请求记录规范

- 完成之后用 git commit 提交
- 小串口：在提交信息中包含用户的原始变更请求（可放在提交说明主体部分），并简述本次处理方式。
- 重大或新增大型功能：将用户的变更请求写入一个与代码相同目录的`<TASK>_REQUESTS.md` 文件；`<TASK>` 使用任务或分支的简明标识。在提交信息中引用该文件路径。
- `<TASK>`命名：使用全大写下划线（snake_case）风格并与分支/任务编号一致，例如`AGENT_MANAGER_REFACTOR`；避免使用 `-`与空格。

## 编码风格

### 不要在注释中重复代码中已经显而易见的内容

不要生成如下评论。```python
# Get current setting
def get_current_setting():
  ...
```相反，只需让函数名称或代码来说明一切：```python
def get_current_setting():
  ...
```### 不要使用幻数/字符串/值

只要有可能，就定义常量来命名幻数/字符串/值，以提高代码的可读性。### Prefer 提前返回

__保持__49__efer：```python
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
```＃＃ Python

- 避免使用`try ... except Exception`来覆盖所有异常，而应该至拦截函数能处理的异常

## Android 应用程序

- 只支持纵向显示；不支持横向显示，因此在紧急情况下考虑兼容横向显示。

- 网络栈存在家具实现：Retrofit/Moshi（`NetServiceMgr` + `I*Api`）与生成的 Inty SDK（`IntyNetworkManager` + `*Service`）同时使用，易导致错误处理/鉴权/环境配置不一致，以及重复创建 `OkHttpClient`。

## __保留__2__

- @<https://developers.cloudflare.com/llms.txt>
- @<https://developers.cloudflare.com/workers/prompt.txt>
- @<https://developers.cloudflare.com/stream/llms-full.txt>
- @<https://developers.cloudflare.com/developer-platform/llms-full.txt>

来自官方文档链接https://developers.cloudflare.com/stream/changelog/

## Agent 架构概述

- 核心对象：`Agent` 负责提示词组装与模型调用；`AgentManager` 负责实例缓存、并发安全、闲置清理与重载。
- 模型配置优先级：优先读取 `settings.llm_config`，阿富汗领域回到全局配置；所有阿富汗价值以全局默认补齐。
- 提示词分层：主提示词（main）、模式提示词（mode，包含 premium Switch）、输出格式提示词（output_format），并在必要时强制使用全局默认。
- 会话历史：使用`chat_history` 表配合 `PostgresChatMessageHistory`；支持相关历史以控制上下文长度。
- 客户端复用：OpenAI客户端封装了LangSmith追踪并做实例级缓存，避免间隙创建客户端。

## 数据模型与模式

- __保留__0__模型`app/models/agent.py`：新增/重点字段
  - 提示词：`main_prompt`, `mode_prompt`
  - 角色卡：`personality`, `scenario`, `message_example`, `creator_notes`, `tags`, `character_version`, `extensions`
  - 语音：`opening_audio_url`
- Pydantic 模型 `app/schemas/agent.py`：
  - 模型配置：`llm_config`（落入 `settings.llm_config` 持久化）
  - 字段序列化：`intro`/`opening` 支持 `{{ char }}`/`{{ user }}` 变量渲染；图片 URL 与尺寸透传资源表信息
- 兼容：`prompt` 字段已废弃，创建/更新时自动迁移到 `personality`；`readable_id`保留但不再展示。

## API 能力（/api/v1/ai/agents）

- 列表/搜索/推荐/关注：`GET /me`、`GET /search`、`GET /recommend`、`POST|DELETE /{agent_id}/follow`
- 详情/创建/更新/删除：`GET /{agent_id}`、`POST /`、`PUT /{agent_id}`、`DELETE /{agent_id}`- 角色卡：导入（JSON/文件）、导出、校验、功能列表
- OpenRouter 模型：仅限超级用户获取模型列表以供体育使用
- 订阅/用量限制：创建代理、文生图、语音生成均接入接入检查与用量记录

## 提示词与卡角色集成

- 支持 SillyTavern V2：字段映射到 Agent 模型，优先级为“角色卡字段 > Legacy prompt”。
- 提示词层次：系统提示词 > 角色卡上下文（`personality`/`scenario`/`message_example`）> 用户信息 > 聊天历史。
- premium 模式：根据`chat_settings.premium_mode`选择不同的模式提示词。

## Extensions 扩展字段

- 统一扩展容器：`agents.extensions`（JSON），前端/后端约定键值结构。
- 头像裁切：`extensions.avatar_crop` 提供裁切坐标，后端序列化时基于 `background`生成裁切头像URL。
- 服务器：策略Agent轻量配置含`extensions`缓存30分钟；更新后激活并触发AgentManager重新加载。

## 图片与资源

- URL 归一化：写库前将 CDN URL 归一化为 GCS 存储路径；读取时按终端类型转换回 CDN。
- 资源尺寸：`resources` 表存储图片尺寸，响应中补齐 `avatar_size`、`background_size`。

## 语音系统

- 壮大：以ElevenLabs为主（可扩展）；创建/更新Agent后异步生成`opening` 的语音并写入 `opening_audio_url`。
- 文本清洗：生成前移除心理/动作描述；支持缓存命中、GCS 存储与用量记录。
- 默认音色：可根据Agent性别选择默认`voice_id`，也可在代理层显式指定。

## 推荐与排序

- 创建支持时间、确定性随机（基于`sort_seed`）、基于评分的平衡随机（`score*2 + hash(seed)%100`）等，策略支持分页。

## 缓存与重载

- AgentData服务器：聊天轻量数据服务器30分钟；更新后失效。
- AgentManager：实例备份、闲置清理、强制重载，保证提示词/配置即时生效。

## 舞台预告（评估）活动

- 前端通过上述接口管理代理/模型并发起问卷；UI支持头像裁切显示与语音试听。

## 配置与性能

- 关键配置：`agent/database/gcs/elevenlabs`段落影响实例池、连接池、上传与生成能力。
- 性能指标：客户端复用、实例服务器、轻量查询与服务器、历史记录、分页与确定性随机、资源/语音服务器。

## 安全/风控与兼容

- RAI：生成图像功能对过滤结果进行说明并先返回原因。
- 兼容：保留遗留字段迁移逻辑；用户信息同步读取路径已废弃标记，规划迁移到用户独立服务。

## 术语

- 代理/角色、角色卡（​​Character Card）、系统/角色/聊天提示词、记忆（Memory）、扩展、开场白（ope​​ning）。

## 关联文档

-`docs/AGENT_CHARACTER_CARD_INTEGRATION.md`
- `docs/CHARACTER_CARD_SYSTEM.md`
- `docs/AGENT_EXTENSIONS_SYSTEM.md`
- `docs/AI_VOICE_SYSTEM.md`
