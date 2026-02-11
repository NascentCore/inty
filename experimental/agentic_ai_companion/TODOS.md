# TODOs

> 记录下一步需要完成的任务，防止遗忘

- [x] 添加 send_zun_long_photo 工具，调用时返回 experimental/agentic_ai_companion/尊龙.png，来测试多个工具调用
- [x] 添加 generate_image 工具（基于 generate_image_from_messages + 最近 10 条消息，Imagen 4 Fast，GEMINI_API_KEY）
- [ ] **API 统一**：将 generate_image 使用的 Imagen 生图逻辑与 app/ 内现有 Imagen/Vertex 生图 API 统一（当前 experimental 直接按 [Gemini API Imagen 文档](https://ai.google.dev/gemini-api/docs/imagen) 实现，未复用 app）
- [x] **语音回复工具**：使用 <https://ai.google.dev/gemini-api/docs/speech-generation> 将 LLM
  返回的消息转化为语音（工具 `text_to_speech`，Gemini TTS，输出 WAV 路径）
- [x] **Clarify user request**：当工具调用的上下文不清晰时向用户询问（experimental 已通过 generate_image 工具描述实现）
  - [ ] **生图前澄清（app 层）**：探索在 app 的 roleplay 系统提示中增加「生图前若上下文不清先澄清」的规则，使行为与 experimental 一致；工具描述仍建议保留，双保险。但是需要测试。
  - [ ] **生图澄清评测脚本**：编写 .py 脚本读取 eval.json，对每条 case 调用 role play API，断言 expected_behavior（clarify 时未调 generate_image，call_generate_image 时已调）及 expected_response_contains_any，便于回归验证提示词效果。
- [ ] **记忆抓取工具**：根据用户反馈，将当前消息中的重要事项记录下来，写入另一个存储，从而在未来交流对话中调用该记忆；
  - [ ] **记忆获取工具**：根据用户反馈，决定从最近哪些核心记忆选项中抓取新的记忆用于后续的聊天交互