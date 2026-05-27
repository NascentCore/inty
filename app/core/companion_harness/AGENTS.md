# Companion Harness

**DO NOT MAINTAIN BACKWARD COMPATIBILITY**

Use LLMs and companion harness to simulate a living person one can only interact through defined medium (app, wechat/weixin, sms, phone-call etc.)

- companion-harness (memories, tools, seeded static prompt slices, etc.) to simulate human emotional behaviors in modality in text (and then audio image video in the future) by dynamically and in a human-like manner to assemble into LLM prompt.

## 架构直觉（不写具体类名）

- **快慢双层思考**：对用户消息既有低延迟的「快响应」，也有可带工具、可多步的「慢思考」路径。Inspired by System I&II (fast & slow).
- **内心节拍（inner tick）**：即使用户不说话，也会周期性唤醒一轮「维护/主动」式推理，支撑自主性与新鲜感。
- **工作记忆（MemoryStore）**：伴侣当下知道的上下文以 semantic and named markdown docs, changes are immediately reflected in the follow-up LLM invocations.
- **关系阶段（context mode）**：从初识引导、到日常陪伴、再到更亲密模式，产品用阶段切换 **约束话术与行为空间**。Help to model a human-like relationship development process.

## Hermes agent wechat/weixin adapater

- We only use wechat/weixin communication protocol, do not allow hermes code to use local filesystem.
