<!-- CREATED_BY_AGENT -->

# 变更记录

## 最小化 Role Play 示例（OpenAI SDK）

### 用途

- 在终端内运行的多轮角色扮演对话示例，作为 agentic AI companion 的起点。
- **仅使用** `app/core/agent/prompts.py` 中的主提示词、模式提示词与 `app/core/agent/prompt_template.py` 的 `render_prompt_jinja2_template` 组装系统消息，**与** `Agent.build_system_messages` **的组装方式一致**（仅 main + mode 两条系统消息，无角色卡、时间上下文等），输出 OpenAI API 所需的 `list[dict]` 消息列表。
- 不依赖 `Agent` 类、数据库或 app 全局配置。

### 运行命令

在**仓库根目录**执行：

```bash
# 方式一：运行 main 入口
python -m experimental.agentic_ai_companion.main

# 方式二：直接运行子模块
python -m experimental.agentic_ai_companion.role_play_minimal
```

需在 `experimental/agentic_ai_companion/.env` 中配置 `OPENROUTER_API_KEY` 或 `OPENAI_API_KEY`（使用 python-dotenv 从该路径加载）。

### 端到端测试运行方式

- 仅组装校验（不调真实 API）：  
  `python -m pytest tests/experimental/agentic_ai_companion/test_role_play_minimal_e2e.py -v`
- 含真实 API 的一轮对话测试（需配置 key，标为 slow）：  
  `python -m pytest tests/experimental/agentic_ai_companion/test_role_play_minimal_e2e.py -v -m slow`
