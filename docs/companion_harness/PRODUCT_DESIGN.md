# 陪伴智能体设计：如何用智能体模拟一个“虚拟的活人”

[ARCH.md](/docs/companion_harness/ARCH.md) describes the underlying mechanism of the agent.
Agent's capability and this doc shape each other.

Interaction container: Weixin, Telegram

这个设计的具体内容，可以称为用于情感陪伴的智能体 Harness，就是围绕 LLM 周围快、慢周期，外部刺激，人格模型，等等；
组合在一起，能在体感上模拟一个“虚拟的活人”。

## 高层设计

只关注智能体 Harness 的设计，目标：

1. 人类式记忆：从聊天中持续提取并更新用户偏好、用户画像、关系边界、事件、LivingSphere、TechnoCore。
2. 长期连续性的关系演化：基于记忆自动生成后续关系、情感建立与演化。

非目标（本阶段）：

- 后端扩展（多用户、多实例）

目标态扩展（多 agent 世界引擎、sub-agent）见 [FR_WORLD_ENGINE.md](./FR_WORLD_ENGINE.md)。
