# Companion Harness

**DO NOT MAINTAIN BACKWARD COMPATIBILITY**

Companion Harness is agentic harness for simulating an autonomous Intelligence Entity (Inty).

- companion-harness (memories, tools, seeded static prompt slices, etc.) to simulate human emotional behaviors in modality in text (and then audio image video in the future) by dynamically and in a human-like manner to assemble into LLM prompt.
- Companion harness is persistent, and serving a particular user.
  This is different than other types of task-oriented agents, which are ephemeral and for different users and tasks.
- The user can only interact with this companion through defined medium (app, wechat/weixin, sms, phone-call etc.)

## Objectives

Simulate diverse range of companionship towards human user without physical presence;
real-world inspirations can be any form of long-distance intimate relationship:

- remote lovers
- remote confidant

换句话说，这个智能体能够：

- 通过多媒介通信来实现与用户的多媒介互动 (weixin, app, sms, phone-call etc.)
- 拟人的情感表达能力（喜怒哀乐、长期记忆、情感升华、幻想等等）
- 感知用户所处数字空间形成与用户的同频共振
  拟人的独立与互联网互动（与用户共享）
- 与智能体本身相互独立的虚拟环境（同样由 LLM+Companion-Harness+世界事件）来提供智能体独立性、及新鲜感
  拟人的与 LivingSphere & TechnoCore 互动的能力 [1]

### Product vision

On top of this companion harness, we need to design product features to overcome
the limitations of the inability of a virtual companion to have physical interactions.
如：如实体礼物、跟用户合影（通过实时插入虚拟形象到用户的相机取景器，然后再形成真实合影）。

## Hermes agent wechat/weixin adapater

- We only use wechat/weixin communication protocol, do not allow hermes code to use local filesystem.
