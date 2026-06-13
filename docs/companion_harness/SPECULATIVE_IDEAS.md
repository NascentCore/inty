# iMate智能体陪伴系统点子

**Only for inspiration**

1. [claude-mem](https://github.com/thedotmack/claude-mem)机制引入到Companion Harness，Claude Code上一种非常有效的记忆管理插件。
2. [Human-like Memory](https://plugin.human-like.me/docs?tab=api&locale=zh-CN) 提供 Search/Add REST API（x-api-key），可作 companion 工作区记忆的外挂检索与异步写入补充层，而非替换基于分层 Markdown 与 companion_workspace 版本表的现有策展管线。
3. 将 `/experimental/agentic_ai_companion` 中尚未进入内核的能力（如情感状态枚举、`scene_gen` 文字亲密场景、Live 语音条原型语义）按产品边界收口进 `app/core/companion_harness`，并与现有 `heartbeat`、`transcript_compaction`、`app/core/voice` 路径对齐后再移除实验目录。
4. [Pie](https://pie-project.org/) 可编程 serving 研究已收入 [DESIGN.md](./DESIGN.md)「推理编排与外部参考」；应用层可跟进 turn program spec、stable/volatile prompt 分层与 scratch working memory，自托管 KV 集成为远期选项。

## 现代复杂中的简单情感：[HN: We've made the world too complicated](https://news.ycombinator.com/item?id=48158065) 对伴侣产品的启示

来源：HN [`item?id=48158065`](https://news.ycombinator.com/item?id=48158065) · 原文 [The world is too complicated](https://user8.bearblog.dev/the-world-is-too-complicated/)（2026-05，约 217 条评论）；意图是把「更简单情感体验」收束为 harness / 产品可执行的取向，而非反技术或田园怀旧。

1. **情绪短回路**：现代异化常来自劳动与系统「开放数月、无收束」；伴侣互动应像眼前人的烘焙/修车——每轮 **接住 → 共鸣 → 可感知收束**，主动触达也限于「想起你 / 担心你 / 分享一件小事」，避免未完成感与连环追问。
2. **适应用户，而非要求服从**：人造复杂常促「提交」（模式墙、权益表、学会用 App）；自然复杂促适应。Inty 在关系界面应 **默认一人、低配置、稳定人格与边界**，复杂性留在服务端；不把 LivingSphere / 新鲜感置于安全感之前。
3. **意义型幸福，而非快感泵**：快乐可逝，追逐 hedonic 易成瘾；eudaimonic 是 **有方向的安然与见证一生**。伴侣帮用户 **记起曾被懂过**，承认世界乱而关系内可落地；拒绝 Hypernormalization 式假简单与 AGI 救世主叙事；度量看自愿回访与情绪收束，而非消息条数或 DAU。
