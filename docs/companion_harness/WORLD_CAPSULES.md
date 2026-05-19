# World Capsule（世界胶囊）

**一句话**：把对话里的共同想象收成可演进的设定单元（胶囊），由 LLM 判断何时巩固进 LivingSphere 或 TechnoCore；**计划中**，见下表。

## 已实现 vs 计划中

| 能力 | 状态 |
| --- | --- |
| 对话即兴 lore（如星图仪含义） | **已实现** — 仅在 `transcript`；不自动进世界正史 |
| `LIVING_SPHERE.md` 种子 + `living_sphere_record_update` → curator | **已实现** — 见 [`LIVING_SPHERE.md`](./LIVING_SPHERE.md) |
| `TECHNO_CORE.md` 宪法注入、`techno_core_record_event` 追加 | **已实现** — 见 [`techno_core/DESIGN.md`](../../techno_core/DESIGN.md) |
| World Capsule 模型与 `world_capsules` 存储 | **计划中** |
| 对话后提取胶囊、`stability` 晋升、prompt 注入待巩固设定 | **计划中** |
| LLM 判断晋升（无「记进小家」等产品门控） | **计划中** |
| 胶囊驱动 LivingSphere / TechnoCore 巩固与交叉校验 | **计划中** |
| 共享 Lore（跨用户集体正史） | **计划中** — 独立后端服务，不进 Inty backend |
| 赛季 / 主题 lore 运营 | **计划中** — 产品向，见 [`COMMERCIALIZATION.md`](../imate/COMMERCIALIZATION.md) |

## 为何要胶囊

共同想象要满足：**可复用**（下轮还能读到）、**可演进**（可改不静默矛盾）、**可分层**（仅 dyad / 小家 / TechnoCore）。

另：**是否跨越感知边界**。例：夸用户一句话 → 不必升格；说 Technosphere 某星爆了 → 进 TechnoCore，须与既有设定**交叉校验**。用户与 AI 可「意愿」进共享现实，但受 **元规则**（constitution + LLM）约束，不靠逐步点选确认。

## 胶囊字段（计划）

| 字段 | 含义 |
| --- | --- |
| `kind` | `artifact` \| `place` \| `rule` \| `relation` \| `event` \| `metaphor` |
| `scope` | `dyad` \| `living_sphere` \| `techno_core` |
| `anchor` | 短标题 |
| `claims` | 一至三条设定陈述 |
| `provenance` | `user_ask` \| `companion_offer` \| `mutual` \| `user_edit` |
| `stability` | `provisional` → `session_canon` → `sphere_canon` → `core_canon` |
| `visibility` | `private` \| `shareable` \| `user_visible` |
| `source_refs` | 可选证据（`user_msg_uuid` 等） |

`stability` = 成熟度渐变，不是用户是否点保存。

## 两层：星图仪例（计划）

| 层 | 内容 |
| --- | --- |
| **LivingSphere** | 小家里的摆设与体验（窗边那台、会拨外环） |
| **TechnoCore** | 世界观里该类器物的一般定义（不绑某一用户坐标） |

同一名字应分 `scope` 或分胶囊，勿混成一条 chat。

## 管道（计划）

`chat` → 提取 `provisional` → dyad 库 → **LLM** 决定是否升入 LivingSphere / TechnoCore → 未来可提交**共享 Lore 服务**。

晋升走今日 `living_sphere_updates` / `techno_core_events` 一类路径的**目标语义**；不做法务式「可分享 / 投票」门控。

## 渐变 morph（计划）

| 速度 | 做什么 |
| --- | --- |
| 即时 | provisional + prompt |
| 回合后 | 合并、冲突、`stability` 上调 |
| 慢速 | curator / 外部 Lore 巩固 |

## 方向

chat 为矿砂，胶囊为砖，砌 LivingSphere / TechnoCore；集体正史走**共享 Lore 服务**，不改 `TECHNO_CORE.md` 宪法。

## Follow-ups

提取触发面、冲突策略、REPL 误粘贴、Launch 叙事、元规则清单。

## See also

[`LIVING_SPHERE.md`](./LIVING_SPHERE.md) · [`techno_core/DESIGN.md`](../../techno_core/DESIGN.md) · [`GLOSSARY.md`](./GLOSSARY.md)
