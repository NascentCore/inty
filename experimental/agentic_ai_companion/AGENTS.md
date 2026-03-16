# Agentic AI Companion

- Use Pydantic models for defining data structures
- 创建 main.py 而不是 @experimental/agentic_ai_companion/__main__.py 隐藏文件
- 模块分工：
  - `chat` 入口与组装
  - `tools` 工具定义与执行
  - `clients` 客户端
  - `prompts` 系统提示词
  - `repl` 同步对话主循环
  - `async_repl` 异步事件驱动 REPL（heartbeat 模式）
  - `heartbeat` 心跳引擎（配置、状态、信号构建）
- Comments should be in Mandarin
- Heartbeat 模式通过 `--heartbeat` 启动，Agent 在用户无输入时定期检查上下文并决定是否主动发消息
