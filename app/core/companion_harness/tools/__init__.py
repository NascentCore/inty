"""Companion Harness 工具层：OpenAI 工具 schema、工具调用执行、后台工具线程、MemoryStore/media 分发器。

LLM function-tool schema 真源在 ``companion_tool_definitions``；执行与 ``build_openai_*`` 在
``companion_tool_runtime``。与 ``companion`` 运行编排协作时从上述模块直接 import，本包
``__init__`` 不做 re-export。

与 `companion` 运行编排协作：`companion.turn` / `prompt_stack` 依赖工具契约与
`tool_background`；本包通过绝对 import 回调 `companion` 中的 LLM、模型与编排辅助，不把
`companion` 当作长期子命名空间来承载工具实现。
"""
