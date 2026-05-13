"""Companion Harness 工具层：OpenAI 工具 schema、工具调用执行、后台工具线程、MemoryStore/media 分发器。

与 `companion` 运行编排协作：`companion.turn` / `prompt_stack` 依赖本包暴露的工具契约与
`tool_background`；本包通过绝对 import 回调 `companion` 中的 LLM、模型与编排辅助，不把
`companion` 当作长期子命名空间来承载工具实现。
"""
