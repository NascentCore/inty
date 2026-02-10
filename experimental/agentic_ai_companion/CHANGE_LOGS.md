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
- 客户端：`OpenAI(base_url=OPENROUTER_BASE_URL, api_key=...)`，模型为 `OPENROUTER_MODEL`（如 `google/gemini-2.5-flash-lite`），角色名/用户名有默认常量（如 `CHAR_NAME` / `USER_NAME`）。
- REPL：读用户输入 → 拼消息 → `client.chat.completions.create`（带 `tools=[send_image]`）→ 若有 tool_calls 则执行工具、追加 assistant + tool 消息并继续请求直到无 tool_calls → 打印助手回复并继续循环。
- **send_image 工具**：无参数，固定发送 `app_icon.png`；执行时在终端打印 `[已发送图片: app_icon.png]`，向 API 返回「已发送图片。」等结果字符串。

### 测试

- **位置**：`tests/experimental/agentic_ai_companion/test_role_play_minimal_e2e.py`
- **内容**：组装校验（条数、role、`{{char}}`/`{{user}}` 已替换、含预期片段）；E2E 一轮对话（`@pytest.mark.slow`，有 key 时调真实 API 断言非空 assistant）。
- **命令**：
  - 仅组装：`python -m pytest tests/experimental/agentic_ai_companion/test_role_play_minimal_e2e.py -v -m "not slow"`
  - 含真实 API：`python -m pytest tests/experimental/agentic_ai_companion/test_role_play_minimal_e2e.py -v -m slow`
