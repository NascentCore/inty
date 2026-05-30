# Companion Harness

**DO NOT MAINTAIN BACKWARD COMPATIBILITY**

Use LLMs and companion harness to simulate a living person one can only interact through defined medium (app, wechat/weixin, sms, phone-call etc.)

- companion-harness (memories, tools, seeded static prompt slices, etc.) to simulate human emotional behaviors in modality in text (and then audio image video in the future) by dynamically and in a human-like manner to assemble into LLM prompt.
- Companion harness is persistent, and serving a particular user.
  This is different than other types of task-oriented agents, which are ephemeral and for different users and tasks.

## Objectives

Simulate emotional intimacy experience without physical presence;
such experience is between human users and AI, but they have real-world patterns as in:

- 异地的爱人/情人
- 异地的知己
- 异地的闺蜜

只是，这个“活人”无法进入物理空间；这需要我们通过创新的产品设计，来无限拟真、缩小与用户的距离感，
如：如实体礼物、跟用户合影（通过实时插入虚拟形象到用户的相机取景器，然后再形成真实合影）。

这个产品的核心是一个基于大语言模型的 Agentic Companion（AI 智能体伴侣），
这个智能体要达到类似”虚拟世界中的活人“的效果。
换句话说，这个智能体能够：

- 拟人的多媒介 (weixin, app, sms, phone-call etc.)
- 拟人的情感表达能力（喜怒哀乐、长期记忆、情感升华、幻想等等）
- 拟人的独立内心世界
- 拟人的独立与互联网互动（与用户共享）
- 拟人的与 LivingSphere & TechnoCore 互动的能力 [1]

The above capability requires:

- 构建多媒介通信来实现与用户的多媒介互动
- 感知用户所处数字空间形成与用户的同频共振
- 与智能体本身相互独立的虚拟环境（同样由 LLM+Companion-Harness+世界事件）来提供智能体独立性、及新鲜感

## Hermes agent wechat/weixin adapater

- We only use wechat/weixin communication protocol, do not allow hermes code to use local filesystem.
