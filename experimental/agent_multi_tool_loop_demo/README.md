# Agent Multi Tool Loop Demo

- 目标: 演示 LLM chat completions 真实产出 tool calls, 并由 loop 顺序执行。
- 场景: "I want to update my profile image"。
- 工具链路: `z_image_generate` -> `update_profile_picture`。

## 演示点

- 由 `chat.completions.create(...)` 返回 `tool_calls`。
- loop 对模型返回的 `tool_calls` 逐个执行(顺序执行, 非并行)。
- 工具结果以 `role=tool` 写回 `messages` 后再进入下一轮推理。
- 推荐模型: `google/gemini-2.5-flash-lite`。

## 运行

```bash
python -m experimental.agent_multi_tool_loop_demo.main \
  --user-request "I want to update my profile image" \
  --model "google/gemini-2.5-flash-lite"
```

## 测试

```bash
pytest -q experimental/agent_multi_tool_loop_demo/tests/test_multi_tool_loop.py
```
