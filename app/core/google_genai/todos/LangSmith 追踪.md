# 添加一个集成了 LangSmith 的 GenAI 客户端生成 API

- [ ] 极简复刻已有官方示例 https://docs.langchain.com/langsmith/trace-with-google-gemini#configure-tracing
      使用 https://github.com/NascentCore/inty/blob/7bb14196261ea8db709c04e2b096d568a8ca95c4/experimental/agentic_ai_companion/clients.py#L25
      确保所有数据都有记录，system instruction、image urls、user prompt，返回图片链接、文本（如有）
- [ ] 验证 nested call 能正常工作，即工具调用都在同一个上下文中，聊天也是
- [ ] 调研 langsmith 是否能跟 resources 数据表进行关联查询
      https://github.com/NascentCore/inty/blob/65eca8cc988f7b1e85f5143236efa978fa1b9397/app/models/resource.py#L24
- [ ] 添加 TODOs 来取消已有的生成图片管理系统，改为从 LangSmith 抽取数据
      app/services/image_generation_service.py
      app/services/resource_service.py
