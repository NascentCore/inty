# Inty Companion Harness — 企业级拟人情感陪伴智能体（后端）

> CREATED_BY_AGENT：本页面向 B2B 售前宣讲，内容对齐仓库 `companion_harness` 生产架构，不含客户端 UI 与订阅计费细节。

---

## 一句话

**Inty 不是「一问一答的客服机器人」，而是可长期陪伴、会记得你、会在你沉默时仍「有自己的日子」的拟人情感智能体后端——企业用自有 App、微信或未来语音/短信渠道接入同一套 Companion Harness 内核即可。**

---

## 客户痛点 → 我们的解法

| 企业场景里的难题 | 传统 LLM 客服 / 角色 Bot | Inty Companion Harness |
| --- | --- | --- |
| 用户聊两轮就流失，没有「被惦记」感 | 无状态或仅会话级上下文 | **关系连续性**：跨会话 MemoryStore（USER / SOUL / MEMORY 等分层记忆） |
| 「像工具不像人」 | 被动应答 | **Inner-tick**：用户空闲时主动搭话（`PROACTIVE_CHAT`）、后台整理记忆（`MAINTENANCE`）、自主推进生活主题（`AUTONOMY`） |
| 无法解释「它为什么这样回」 | 黑盒 prompt | **可追溯**：回合、记忆版本、工具副作用、LangSmith trace 可审计 |
| 渠道一换就要重做大脑 | 各端各做一套 | **媒介无关回合**：内核与传输分离；生产文本通道为 `/api/v1/chat/ws`，微信等走 adapter |

---

## 产品是什么（只谈后端智能体）

**Companion Harness** = 围绕大模型（LLM）组装的 **agentic harness**，目标是在数字媒介上持续模拟「虚拟活人」的情感陪伴体验，而非完成单次任务。

核心能力（已实现或正在生产路径上）：

1. **长期关系记忆**
   - 三层时间尺度：episodic（当日流水）→ gist（当日纪要）→ semantic（跨日关系认知）
   - 长期画像：USER（对用户的理解）、SOUL（伴侣基调与边界）
   - 体验门控：私人陪伴 vs 角色扮演可控制「是否注入私人记忆」

2. **拟人节律与自主性**
   - 用户在线：前台快速对话 + 后台工具慢思考（`tool_background`），不阻塞主回复
   - 用户沉默：inner-tick 调度主动消息、定时提醒、记忆维护、自主生活线（`LIFE_CURRENTS.md`）
   - Bootstrap：交互式建立 companionship 类型与人设，再进入稳定陪伴模式

3. **虚拟世界与独立性**
   - **LivingSphere**：企业与用户可共建的「虚拟小家」快照（用户明确指令可改）
   - **TechnoCore**：伴侣集体虚拟世界事件（只读注入，增强「她也有自己的世界」）

4. **工具与多模态扩展**
   - 网页检索、读页、生图等工具链；生成物与提示可落库追溯
   - 架构预留语音/图片/电话等媒介，统一进入同一 **companion turn** 语义

5. **企业可集成的对外边界**
   - 主入口：**WebSocket** `/api/v1/chat/ws`（契约：`app/schemas/chat_websocket.py`）
   - 编排与鉴权在 `app/` 应用层；「大脑」在 `app/core/companion_harness/`
   - 行为与模型路由可通过 **config.yaml** 按环境/客户策略配置（非硬编码关键词规则）

---

## 典型 B2B 场景（宣讲时可按需勾选）

- **银发与居家关怀**：子女无法 7×24 在场时的情感倾诉与日常惦记（需客户自有合规与人工兜底流程）
- **员工关怀 / EAP 延伸**：高压岗位下的匿名倾诉伴侣，降低羞耻感门槛（记忆 scope 可按企业租户隔离部署）
- **保险、康养、教育机构的「粘性陪伴层」**：在现有 App 内嵌 Inty 内核，提升日活与续费理由（情绪价值，非替代专业诊疗）
- **品牌 IP 虚拟伴侣**：用企业人设 seed IDENTITY / STYLE，由 Harness 维持一致语气与关系演化
- **微信 / 企微触达**：Ops 侧已有 WeChat bridge 验证路径，适合「在用户已有社交习惯里陪伴」的 PoC

---

## 与「通用 Agent / Copilot」的差异（销售话术要点）

1. **Persistent，非 Ephemeral**：一个 companion 长期服务一个用户，不像任务型 agent 用完即弃。
2. **情感编排优先于任务完成**：prompt 切片、记忆管线、inner-tick 均为「关系」设计，不是工单 SLA。
3. **传输可替换，人格不可分裂**：换 App、换 WS 连接，同一 MemoryStore scope 延续同一段关系。
4. **可观测、可运营**：运维可对照 Postgres 记忆文档版本与 LangSmith 排查「这一轮为何这样回」。

---

## 交付形态（对企业客户）

| 层级 | 说明 |
| --- | --- |
| **内核授权 / 私有化部署** | 部署 Inty 后端（`backend/inty` 或 Ops 变体），数据库 Postgres，按租户配置 `config.yaml` |
| **API 集成** | 客户自有客户端对接 WebSocket 协议；或由我方/iMate 壳做参考实现 |
| **定制** | 人设模板（IDENTITY / STYLE / SOUL）、companionship 模式、safety 策略、模型供应商路由 |
| **PoC 建议** | 单租户、单 companion 实例、文本通道先行；2–4 周可验证「记忆 + 主动搭话 + 可追溯」 |

---

## 技术可信度（给技术决策人一页以内）

```text
客户端 (App / 微信 adapter / REPL)
        ↓
/api/v1/chat/ws  →  companion_chat_service
        ↓
Companion Harness (Session → Turn → MemoryStore → Tools → LLM)
        ↕
Postgres (companion_memory_document_versions) + living_sphere + techno_core
```

- 生产聊天路径 **仅** 使用 companion harness + living_sphere + techno_core（维护模式下的旧角色卡路径不在此销售范围）。
- CI 覆盖后端层检查、Alembic 迁移、WebSocket 冒烟；适合企业内网二次硬化（认证、加密、审计）后上线。

---

## 合规与边界（售前必讲，避免过度承诺）

- 本产品定位为 **情感陪伴与倾诉支持**，**不替代** 执业医师、心理咨询师或危机干预热线。
- Harness 设计文档将 **Security** 标为非目标；企业合同须单独约定数据驻留、脱敏、留存周期与内容安全策略（可叠加客户侧审核与 SAFETY prompt 层）。
- 主动消息（proactive）需与客户产品的通知许可、勿扰策略对齐。

---

## 下一步（Call to Action）

1. 选定 **1 个垂直场景 + 1 条接入渠道**（建议 WebSocket 文本 PoC）。
2. 提供 **品牌人设草案** 与 **禁止话题/升级人工** 规则。
3. 安排 **技术对接工作坊**（WS 契约、鉴权、租户隔离、观测对接）。
4. 用 **inty_v2_repl 或 iMate** 对照演示同一后端行为，缩短「听懂了」到「看见了」的距离。

---

**联系与材料**：架构详解见仓库 `docs/companion_harness/ARCH.md`、`DESIGN.md`、`MEMORY_PIPELINE.md`；本页仅作对外销售摘要。
