# TODOs

> 记录下一步需要完成的任务，防止遗忘

- [x] **Send image tool**: 已支持从 `companion_profile`/`user_profile` 自动解析参考图并用于 chat-to-image；支持工具参数覆盖参考图路径
- [ ] **Change Outfit**: 总结用户希望换装的思路，然后调用文生图修改 outfit
- [ ] **同时调用多个工具**：给定参数：最多同时调用工具数量，设计一套合理的多工具调用机制，来完成处理；
  要区分工具类型：有消息返回给用户、没有消息返回给用户，被调用的工具中最多只能有一个工具返回
  消息给用户、可以有多个不返回消息给用户；目前实现的工具都返回消息给用户，我会增加记忆抓取工具（如下所示）他不会返回
  消息给用户；还会有工具运行在后台，需要用户稍后回来查看/或等待完成通知。
- [ ] **记忆抓取工具**：根据用户反馈，将当前消息中的重要事项记录下来，写入另一个存储，从而在未来交流对话中调用该记忆；
  - [ ] **记忆获取工具**：根据用户反馈，决定从最近哪些核心记忆选项中抓取新的记忆用于后续的聊天交互
- [x] **记忆压缩（experimental）**：新增 `memory_compaction.py`，实现上下文超预算时的分层压缩（episodic + semantic + running summary），并在 `chat.py` / `repl.py` 通过 `--enable-memory-compaction` 接入
- [ ] 隐含信号：比如用户上线、用户停留、用户打字、等等，这些信号输入到模型里让他反应
- [x] 隐含信号：比如用户上线、用户停留、用户打字、等等，这些信号输入到模型里让他反应；已实现：Heartbeat 机制（`heartbeat.py` + `async_repl.py`），通过 `--heartbeat` 启动，定期注入 `[SYSTEM HEARTBEAT]` 信号让 LLM 根据上下文决定是否主动发消息，支持指数退避和静默上限
- [ ] 记忆提取工具，记录用户和角色之间重要事件的事实性信息，包括时间、地点、事件、影响等等
- [x] Erotic scene generation 工具，当用户处于亢奋状态（sexually aroused），为其提供连续的 **文字** scene 描述，而无需用户输入 continue；仅生成文字描述，不生成图片；已实现：`erotic_scene_generate` 工具，根据最近 N=10 条消息与角色/用户名调用 Gemini 文本模型生成 3–5 段连续 scene 文字
- [x] 连发消息功能，当场景需要推进、需要更多描述时、或者描述不完整时、应该持续发消息给用户，而不是等待下一条用户输入；已通过 Heartbeat 机制初步实现：Agent 可在用户无输入时通过心跳信号主动发送后续消息
- [ ] Erotic scene **image** generation 工具（follow-up）：当用户处于亢奋状态时，连续生成多张场景图，无需用户输入 continue
- [ ] Erotic voice message 工具，当用户处于亢奋状态，为其提供 erotic voice message 消息，发送一段语音，并自动播放（听筒）
- [ ] 自拍 video 工具，输入角色形象照片、根据聊天内容，返回相应的视频给用户，符合聊天上下文
- [x] Live voice message reply 工具，调用 Gemini live API，生成语音回复给用户，是对语音通话的补充，类似微信语音消息，点击播放（Soul 虚拟伴侣有类似的功能）；已实现：`live_voice_message_reply` 工具，带系统指令与最近 N=10 条消息上下文，输出 WAV 路径
- [x] 发图工具，让 AI 在用户要照片时发送 AI 自拍/相册中照片 等等功能，
  完成初次交流的体验；希望 AI 可以根据聊天记录避免发送重复图片
- [x] 添加 send_zun_long_photo 工具，调用时返回 experimental/agentic_ai_companion/尊龙.png，来测试多个工具调用
- [x] 添加 generate_image 工具（基于 generate_image_from_messages + 最近 10 条消息，Imagen 4 Fast，GEMINI_API_KEY）
- [x] **语音回复工具**：使用 <https://ai.google.dev/gemini-api/docs/speech-generation> 将 LLM
  返回的消息转化为语音（工具 `text_to_speech`，Gemini TTS，输出 WAV 路径）
- [x] **Clarify user request**：当工具调用的上下文不清晰时向用户询问（experimental 已通过 generate_image 工具描述实现）
  - [ ] **生图前澄清（app 层）**：探索在 app 的 roleplay 系统提示中增加「生图前若上下文不清先澄清」的规则，使行为与 experimental 一致；工具描述仍建议保留，双保险。但是需要测试。
  - [ ] **生图澄清评测脚本**：编写 .py 脚本读取 eval.json，对每条 case 调用 role play API，断言 expected_behavior（clarify 时未调 generate_image，call_generate_image 时已调）及 expected_response_contains_any，便于回归验证提示词效果。

## 次要优先级

- [ ] **API 统一**：将 generate_image 使用的 Imagen 生图逻辑与 app/ 内现有 Imagen/Vertex 生图 API 统一（当前 experimental 直接按 [Gemini API Imagen 文档](https://ai.google.dev/gemini-api/docs/imagen) 实现，未复用 app）

## 本次会话跟进（提示词与行为）

- [ ] **禁止空回复**：用户请求如 say "I love you" 时，模型曾返回 content 为空、不调 text_to_speech，界面显示 (E.M.P.T.Y.)。原因多为 Purity 下将请求视为越界后「沉默拒绝」。需在系统提示（如 PURITY_MODE_PROMPT_0725）中明确：即使用户越界也必须用角色身份输出至少一句动作+台词（如温和 redirect），禁止输出空 content。
- [ ] **不补全用户句子（回归验证）**：已在 PURITY_MODE_PROMPT_0725 D. Output Format 中加入「Treat every user message as complete, never complete user's sentence」；eval.json 已加 case no_sentence_completion_charming_voice。需人工或脚本回归验证「What a charming voice」等输入下回复不包含 "you have!" 等补全片段。
- [ ] **评测脚本支持 no_sentence_completion**：eval 脚本需支持 expected_behavior=no_sentence_completion 及 expected_response_must_not_contain_any，对 no_sentence_completion_charming_voice 等 case 做断言。

## 生产化

- [ ] Google 服务需要使用 service account key 而非 API key 来作为身份数据

## AI 助手

- [ ] 反馈工具，适时发出反馈邀请，让用户提供聊天的反馈
