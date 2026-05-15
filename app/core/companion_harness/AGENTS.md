# Companion Harness：伴侣智能体的运行时

**一句话**：把 Inty 变成「会对用户说话、也会自己琢磨」的 **单一逻辑主体**——负责多通道响应、记忆持久化，以及来自 LivingSphere / TechnoCore 的合成刺激。

## 读者与边界

- 读者：要理解或修改 **伴侣推理主循环、记忆、inner-tick、工具** 的编码智能体与后端核心工程师。
- 边界：产品级 HTTP/WS 外壳在 `app/api`；本包专注 **会话级智能体语义**。

## 架构直觉（不写具体类名）

- **快慢双层思考**：对用户消息既有低延迟的「快响应」，也有可带工具、可多步的「慢思考」路径。
- **内心节拍（inner tick）**：即使用户不说话，也会周期性唤醒一轮「维护/主动」式推理，支撑自主性与新鲜感。
- **工作记忆（MemoryStore）**：伴侣当下知道的上下文以结构化文档形式维护，并 **实时落库**，慢思考与 inner tick 的写入对后续轮次 **立即可见**。
- **关系阶段（context mode）**：从初识引导、到日常陪伴、再到更亲密模式，产品用阶段切换 **约束话术与行为空间**。

## Tips

- Cleaning data (prompts, tool descriptions, orchestration) to make agents reliable & predictable
