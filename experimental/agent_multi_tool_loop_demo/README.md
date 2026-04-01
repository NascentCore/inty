# Agent Multi Tool Loop Demo

- 目标: 演示一个 agent loop 在同一轮内触发多个 tool call。
- 场景: "I want to update my profile image"。
- 工具链路: `z_image_generate` -> `update_profile_picture`。

## 演示点

- 第 1 轮 assistant 返回 2 个工具调用:
  - `z_image_generate(prompt, style)`
  - `update_profile_picture(image_url="$tool:z_image_generate.image_url")`
- 运行时先执行生图工具, 再把产出的 `image_url` 注入头像更新工具。
- 第 2 轮 assistant 给出最终文本, loop 结束。

## 运行

```bash
python -m experimental.agent_multi_tool_loop_demo.main \
  --user-request "I want to update my profile image"
```

## 测试

```bash
pytest -q experimental/agent_multi_tool_loop_demo/tests/test_multi_tool_loop.py
```
