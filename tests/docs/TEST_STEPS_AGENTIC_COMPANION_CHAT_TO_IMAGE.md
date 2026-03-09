# TEST_STEPS_AGENTIC_COMPANION_CHAT_TO_IMAGE

## Goal

验证 `experimental/agentic_ai_companion` 中 `generate_image` 工具已复刻 `app/` 聊天生图关键行为：  
- 基于最近对话构建 prompt  
- 使用 AI/用户参考图生图  
- 429 自动模型回退  
- 失败时按提示词相似度复用历史图兜底

## Automated checks

1. 运行单元测试：

`pytest experimental/agentic_ai_companion/tests/test_image_gen.py -q`

## Manual checks (optional)

1. 在 `experimental/agentic_ai_companion/companion_profile/` 放置 `avatar.jpg`（或 `avatar.png`）；
2. 在 `experimental/agentic_ai_companion/user_profile/` 放置 `avatar.jpg`（或 `avatar.png`）；
3. 运行 `python -m experimental.agentic_ai_companion.main`；
4. 输入一句明确生图请求（例如：“Generate an intimate role-play image where we hug near a window.”）；
5. 观察工具返回：
   - 终端应打印图片路径；
   - 返回文案中应包含 metadata 路径；
   - metadata 内应含 `prompt`、`reference_image_urls`、`model` 字段。
