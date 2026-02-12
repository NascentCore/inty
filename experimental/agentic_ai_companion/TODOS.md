# TODOs

> 记录下一步需要完成的任务，防止遗忘

- [ ] 自拍 video 工具，输入角色形象照片、根据聊天内容，返回相应的视频给用户，符合聊天上下文
- [ ] Live voice message reply 工具，调用 Gemini live API，生成语音回复给用户，是对语音通话的补充，类似微信语音消息，点击播放（Soul 虚拟伴侣有类似的功能）
- [ ] 自拍 photo 工具，让 AI 在用户要照片时发送 AI 自拍/相册中照片 等等功能，
  完成初次交流的体验；希望 AI 可以根据聊天记录避免发送重复图片
- [x] 添加 send_zun_long_photo 工具，调用时返回 experimental/agentic_ai_companion/尊龙.png，来测试多个工具调用
- [x] 添加 generate_image 工具（基于 generate_image_from_messages + 最近 10 条消息，Imagen 4 Fast，GEMINI_API_KEY）
- [x] **语音回复工具**：使用 <https://ai.google.dev/gemini-api/docs/speech-generation> 将 LLM
  返回的消息转化为语音（工具 `text_to_speech`，Gemini TTS，输出 WAV 路径）
- [x] **Clarify user request**：当工具调用的上下文不清晰时向用户询问（experimental 已通过 generate_image 工具描述实现）
  - [ ] **生图前澄清（app 层）**：探索在 app 的 roleplay 系统提示中增加「生图前若上下文不清先澄清」的规则，使行为与 experimental 一致；工具描述仍建议保留，双保险。但是需要测试。
  - [ ] **生图澄清评测脚本**：编写 .py 脚本读取 eval.json，对每条 case 调用 role play API，断言 expected_behavior（clarify 时未调 generate_image，call_generate_image 时已调）及 expected_response_contains_any，便于回归验证提示词效果。
- [ ] **记忆抓取工具**：根据用户反馈，将当前消息中的重要事项记录下来，写入另一个存储，从而在未来交流对话中调用该记忆；
  - [ ] **记忆获取工具**：根据用户反馈，决定从最近哪些核心记忆选项中抓取新的记忆用于后续的聊天交互

## 次要优先级

- [ ] **API 统一**：将 generate_image 使用的 Imagen 生图逻辑与 app/ 内现有 Imagen/Vertex 生图 API 统一（当前 experimental 直接按 [Gemini API Imagen 文档](https://ai.google.dev/gemini-api/docs/imagen) 实现，未复用 app）

## 本次会话跟进（提示词与行为）

- [ ] **禁止空回复**：用户请求如 say "I love you" 时，模型曾返回 content 为空、不调 text_to_speech，界面显示 (E.M.P.T.Y.)。原因多为 Purity 下将请求视为越界后「沉默拒绝」。需在系统提示（如 PURITY_MODE_PROMPT_0725）中明确：即使用户越界也必须用角色身份输出至少一句动作+台词（如温和 redirect），禁止输出空 content。
- [ ] **不补全用户句子（回归验证）**：已在 PURITY_MODE_PROMPT_0725 D. Output Format 中加入「Treat every user message as complete, never complete user's sentence」；eval.json 已加 case no_sentence_completion_charming_voice。需人工或脚本回归验证「What a charming voice」等输入下回复不包含 "you have!" 等补全片段。
- [ ] **评测脚本支持 no_sentence_completion**：eval 脚本需支持 expected_behavior=no_sentence_completion 及 expected_response_must_not_contain_any，对 no_sentence_completion_charming_voice 等 case 做断言。

## 生产化

- [ ] Google 服务需要使用 service account key 而非 API key 来作为身份数据
