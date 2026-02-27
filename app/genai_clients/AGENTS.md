# GenAI 客户端

各类外部生成式 AI API Clients 汇聚在这个文件，统一管理，目前为每个客户端实例提供 LangSmith Tracing
并且管理全局共享实例

各类 SDK 使用情况：

- 文本类大模型客户端使用 Openai SDK，支持较广、并且已经使用很长时间，修改比较麻烦
- 文生图大模型客户端使用原厂 SDK：Google GenAI（nanobanana）、OpenAI（gpt image）、falai（开源生图模型）
- 实时语音通话：Google GenAI（Gemini Live API）

- [ ] 迁移 OpenAI Client 客户端到此目录
- [ ] 迁移 Google GenAI 客户端到此目录
- [ ] 迁移 falai 客户端到此目录
