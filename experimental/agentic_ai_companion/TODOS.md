# TODOs

> 记录下一步需要完成的任务，防止遗忘

- [x] 添加 send_zun_long_photo 工具，调用时返回 experimental/agentic_ai_companion/尊龙.png，来测试多个工具调用
- [x] 添加 generate_image 工具（基于 generate_image_from_messages + 最近 10 条消息，Imagen 4 Fast，GEMINI_API_KEY）
- [ ] **API 统一**：将 generate_image 使用的 Imagen 生图逻辑与 app/ 内现有 Imagen/Vertex 生图 API 统一（当前 experimental 直接按 [Gemini API Imagen 文档](https://ai.google.dev/gemini-api/docs/imagen) 实现，未复用 app）
