# `agentic_ai_companion/`：早期 Agentic REPL 实验

**一句话**：独立 Python 包探索 **工具型对话 + 可选心跳式主动消息**；结构上分 **chat / tools / clients / prompts / repl / async_repl / heartbeat** 等职责块。

## 习惯

- **数据**：Pydantic 建模。
- **入口**：使用可见的 `main.py` 作为 CLI 入口，而非隐藏 `__main__.py`。
- **注释语言**：中文。
- **心跳模式**：`--heartbeat` 下，用户沉默时也会周期性检查上下文并决定是否主动发言——产品语义上接近后来的 **inner-tick**，但实现无关化。
