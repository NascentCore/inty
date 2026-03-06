# TEST_STEPS_AGENTIC_LOOP_SLEEP_DEMO

## 目标

验证 `experimental/agentic_loop_sleep_demo/main.py` 的核心行为：

1. LLM 先触发 `sleep` 工具调用
2. `sleep` 工具根据上下文中的秒数执行等待
3. 工具结果回填到 messages
4. agentic loop 再次调用 LLM，并得到最终回复

## 前置条件

- 在仓库根目录有 `.env`
- `.env` 中包含 `OPENROUTER_API_KEY`

## 执行命令

```bash
python -m experimental.agentic_loop_sleep_demo.main \
  --user-request "请先 sleep 2 秒，然后告诉我你回来了" \
  --model "z-ai/glm-4.5-air:free" \
  --max-steps 4
```

## 通过标准

- 输出中出现 `LLM 触发了 1 个工具调用`
- 输出中出现 `执行工具: sleep`
- 输出中工具返回包含 `"requested_seconds": 2`
- 下一轮出现 `LLM 最终回复`
- 最后出现 `Agentic loop 结束：本轮没有 tool call`

