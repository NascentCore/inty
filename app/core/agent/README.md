# agent - 智能体核心

## Cursor Summary

- 目录用途: 智能体（Agent）核心封装，包括提示模板、拼装逻辑与统一入口。
- 关键文件:
  - `prompts.py`: 提示片段与组合工具。
  - `prompt_template.py`: 提示模板与变量化支持。
  - `agent.py`: 智能体构造与对话配置入口。
- 关联: 与 `core/prompting` 的素材集合、`services/chat_service.py` 的推理流程、`utils/*` 的模型客户端配合使用。
