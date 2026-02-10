<!-- CREATED_BY_AGENT -->

# 变更记录

## 最小化 Role Play 示例（OpenAI SDK）

### 定位

- **最小化 Role Play 示例**：在终端内用 OpenAI 兼容 API 做多轮角色扮演，作为 agentic AI companion 的起点。
- **提示词来源**：仅用 `app/core/agent/prompts.py` 的 main/mode（当前为 `PURITY_ROLEPLAY_PROMPT`）与 `app/core/agent/prompt_template.render_prompt_jinja2_template` 拼 2 条系统消息，与 `Agent.build_system_messages` 的 main+mode 一致，不依赖 Agent、DB 或 app 配置。

### 目录与入口

| 文件 | 说明 |
|------|------|
| **main.py** | 显式入口，调用 `role_play_minimal.main()` |
| **role_play_minimal.py** | 核心：组系统消息、建 OpenAI client、REPL 循环 |
| **__init__.py** | 包声明 |
| **.env** | 本地环境变量（含 `OPENROUTER_API_KEY`），由 python-dotenv 按显式路径加载 |
| **CHANGE_LOGS.md** | 本文件：用途、运行命令、与 build_system_messages 的对应关系、测试命令 |
| **README.md** | 项目愿景与当前可运行命令（main.py） |
| **AGENTS.md** / **思辨.md** | 本目录约定与思考记录 |

### 运行方式

在**仓库根目录**执行：

```bash
# 方式一：运行 main 入口
python -m experimental.agentic_ai_companion.main

# 方式二：直接运行子模块
python -m experimental.agentic_ai_companion.role_play_minimal
```

**前置条件**：`experimental/agentic_ai_companion/.env` 存在，且配置 `OPENROUTER_API_KEY`（当前实现仅使用 OpenRouter）。

### 当前实现要点（role_play_minimal.py）

- 启动时：`load_dotenv(_ENV_PATH)`，且 `assert _ENV_PATH.exists()`、`assert os.getenv("OPENROUTER_API_KEY") is not None`。
- 系统消息：`build_system_messages_openai(char_name, user_name)` 返回 2 条 `{"role": "system", "content": "..."}`，供脚本与测试共用。
- 客户端：`OpenAI(base_url=OPENROUTER_BASE_URL, api_key=...)`，模型为 `OPENROUTER_MODEL`（当前默认 `google/gemini-2.5-flash`），角色名/用户名有默认常量（如 `CHAR_NAME` / `USER_NAME`）。
- REPL：读用户输入 → 拼消息 → `client.chat.completions.create`（带 `tools=[send_app_icon]`）→ 若有 tool_calls 则执行工具、追加 assistant + tool 消息并继续请求直到无 tool_calls → 打印助手回复（含「点击打开: \<path\>」若本轮执行了 send_app_icon）并继续循环。
- **send_app_icon 工具**：无参数，固定发送 `app_icon.png`；成功时返回「已发送图片。」及绝对路径，路径作为当轮聊天回复的一部分展示，供用户点击打开。

### 测试

- **位置**：`tests/experimental/agentic_ai_companion/test_role_play_minimal_e2e.py`
- **内容**：组装校验（条数、role、`{{char}}`/`{{user}}` 已替换、含预期片段）；E2E 一轮对话（`@pytest.mark.slow`，有 key 时调真实 API 断言非空 assistant）。
- **命令**：
  - 仅组装：`python -m pytest tests/experimental/agentic_ai_companion/test_role_play_minimal_e2e.py -v -m "not slow"`
  - 含真实 API：`python -m pytest tests/experimental/agentic_ai_companion/test_role_play_minimal_e2e.py -v -m slow`

## send_app_icon 与 REPL 体验更新（近期）

### 变更摘要

- **图片路径作为聊天回复**：`send_app_icon` 执行成功后，图片的绝对路径作为当轮助手回复的一部分显示（在「AI Companion>」下追加一行「点击打开: \<path\>」），用户可在终端中点击路径用系统默认程序打开。不再单独打印中间结果行。
- **工具描述强化**：`send_app_icon` 的 description 中明确「当用户明确要求发送图片、图标或 app icon 时，必须调用本工具，仅用文字回复无法真正发出图片」，以提升模型在用户索图时调用工具的比例。
- **REPL 完整回复**：若 API 返回含 tool_calls，会先打印该条助手文本（若有），再继续执行工具并请求下一轮；若最终 content 为空则显示 fallback「（已通过 send_app_icon 发送图片。）」并附带路径。
- **详细日志**：使用标准库 `logging` 在 REPL 全流程打点（启动、系统消息、每轮用户输入、每次 API 请求/响应与 has_tool_calls、send_app_icon 执行与路径、每轮结束与是否附带路径、退出），便于记录与排查执行情况。默认级别 INFO。
- **默认模型**：`OPENROUTER_MODEL` 由 `google/gemini-2.5-flash-lite` 改为 `google/gemini-2.5-flash`。lite 在「用户要图时稳定调用 send_app_icon」上表现不稳定，改用 2.5-flash 后工具调用更可靠。

### 实现细节（role_play_minimal.py）

- `execute_send_app_icon()` 返回 `(result_str, path_str | None)`，不再在函数内打印；路径由调用方并入当轮展示。
- `process_response_with_tools` 增加第五项返回值：本轮若执行了 send_app_icon 且成功则返回该图片绝对路径，用于 REPL 在 done 时拼入 display。
- REPL 内层循环维护 `pending_image_path`，在 done 时若非空则 `display = content + "\n点击打开: " + pending_image_path`。
- 日志格式：`%(asctime)s [%(levelname)s] %(name)s: %(message)s`，datefmt 到秒。

### 架构微调（role_play_minimal.py）

- **工具定义与执行器统一**：引入 Pydantic 模型 `ToolDefinition`（name, description, parameters, executor），`executor` 使用 `Field(exclude=True)` 仅运行时使用、不序列化。单一列表 `TOOL_DEFINITIONS` 维护所有工具，从中推导 `SEND_IMAGE_TOOLS`（OpenRouter schema）与 `TOOL_EXECUTORS`（name → executor）；删除 `_register_tools()`，新增/修改工具只改 `TOOL_DEFINITIONS` 一处即可保持 schema 与执行器一致。
- **ProcessedResponse（Pydantic 模型）**：单轮 API 响应处理结果由 5 元组改为不可变 Pydantic `BaseModel`（messages, content, done, assistant_text, image_path），REPL 使用 `out.messages`、`out.done`、`out.content` 等，可读性更好；依赖 `pydantic>=2`。
- 移除废弃注释（如原 `OPENROUTER_MODEL` 的 lite 备选）。
