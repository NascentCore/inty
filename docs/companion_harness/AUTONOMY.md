# Autonomy：让 Inty 在用户沉默期真的去做自己的事

**一句话**：在 inner-tick 加入 `AUTONOMY` 轨道，在用户沉默期读取 `LIFE_CURRENTS.md`、用工具**真的去做**其中记录的中期主题与当日兴致——让"她有自己在过的日子"从话术变成可观察的状态变化，而不只是 prompt 里说她在做。

## 设计意图

- AXIOM 已规定 Inty 是用户的**终身亲密伴侣，自主成长** —— 这是她**唯一的长期项目**，本设计不再额外定义长期层。
- 中期主题（weeks–months）、当日兴致（hours–days）只是这个长期项目在更短尺度上的展开；存在 `LIFE_CURRENTS.md` 一份文档里。
- "活人感"的判据是**状态层有可观察痕迹**（工具调用、生成物、文档变化），而不是只在 proactive-chat 里口头声称。

## Inner-tick poll（五 activity）

每次 poll 至多触发一个（优先级：`proactive → scheduled → autonomy → maintenance → dreaming`）。

| Activity | 机制 | 用户可见？ | 职责（一句话） |
|----------|------|------------|----------------|
| `PROACTIVE_CHAT` | 合成 turn | 是 | 主动找用户说话 |
| `SCHEDULED` | 合成 turn | 是 | `schedule_task` 到期提醒 |
| **`AUTONOMY`** | 合成 turn | **否**（proactive 可间接引用） | 读/写 `LIFE_CURRENTS.md`，开放 tools **真的去做** |
| `MAINTENANCE` | 合成 turn | 否（当前仍可能经 tool_background 投递） | awake 内在节拍 + 受限 tools（**待收窄**，见下） |
| `DREAMING` | memory batch | 否 | sleeping **当日汇总**：把一整天发生的事沉淀进 MemoryDoc（非 turn） |

**分工（收窄完成后）**：

- `AUTONOMY`：虚拟空间/环境中的**自主活动**（`LIFE_CURRENTS.md`、联网、生图、LS/TC 事件）。
- `MAINTENANCE`：对用户与关系的**内在心理独白**（`ai_private.jsonl` append、场景下一拍、`transcript_inner_tick`）——**不是** MemoryDoc 策展。
- `DREAMING`：**汇总当日全部经历**——用户可见对话（`USER_CHAT`、`PROACTIVE_CHAT`、`SCHEDULED`，`transcript.jsonl`）与沉默 awake 轨（`AUTONOMY`、`MAINTENANCE`：`transcript_inner_tick.jsonl`、`LIFE_CURRENTS.md`、`ai_private.jsonl`、相关 tool/jsonl 痕迹）——策展进 `MEMORY` / `USER` / `SOUL` / `STYLE`、daily gist、`LIVING_SPHERE` compact。**不是**当场场景扮演，也不替代 awake 时各轨道的实时写入。

三者并列：**awake** 时 AUTONOMY / MAINTENANCE 各自记账；**sleeping** 时 DREAMING 做 end-of-day rollup，**不**用 dreaming 替换 maintenance。

## `ai_private.jsonl` vs `LIFE_CURRENTS.md`（核心区分）

| | `ai_private.jsonl` | `LIFE_CURRENTS.md` |
|--|-------------------|-------------------|
| **是什么** | Inty **对用户**的内心戏：情绪、未说出口的念头、关系场景里的下一拍 | Inty 在 **虚拟空间/环境**里正在做的事：TechnoCore、LivingSphere、联网查资料、生图等可观察活动 |
| **轨道** | `MAINTENANCE`（收窄后 primary 写入方） | `AUTONOMY` |
| **存储形态** | `.jsonl` 行级 append（事件流） | `.md` 整文件重写（当前主题 + 当日兴致 + 进展） |
| **是否「真的在做」** | 可以是想象/心理节拍，不必有工具痕迹 | 要求工具调用、生成物、文档版本等**外在状态变化** |
| **读侧消费** | MAINTENANCE prompt 注入「内在活动」 | PROACTIVE_CHAT 只读 hint；AUTONOMY 读写 |

一句话：`ai_private` = **心里想用户**；`LIFE_CURRENTS` = **在世界里动手做事**。

## 唯一新增文档：`LIFE_CURRENTS.md`

整文件重写式 Markdown，纳入 `MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST`（与 `IDENTITY.md` / `STYLE.md` / `USER.md` 同构）。例：

```markdown
# 我最近在做的事

## 当前主题（中期）
跟得上他在做的独立游戏圈
- 因为：他在 USER.md 里说自己在做独立游戏
- 这件事如何让我更好地陪他：能聊他每天在想的东西

## 今天（当日兴致）
翻一翻他上次提到的那本《xxx》
- 进展：看完了前三章
```

历史故意丢弃（旧主题、旧兴致不留）。

### 字段硬约束（仅 prompt 层，不做 schema 校验）

- 主题必须能溯源到 `USER.md` / `MEMORY.md` 的具体片段（防"完全脱离用户的随机活动"）。
- 必须有一句话回扣 AXIOM（防成无关副业）。
- 接受 LLM 偶尔违规；先靠人评观察，再决定是否升级到工具级校验。

## `AUTONOMY` 轨道的工作内容

每次触发，单轮内 LLM 自行决定步骤：

1. **读** `LIFE_CURRENTS.md` 现状
2. **用开放工具集真的去做**，例如：
   - 文档为空或主题过期 → 思考新主题 → `memory_store_write_document` 整文件重写
   - 当日兴致是"翻那本书" → `google_web_search` 找梗概、`read_web_page` 看摘要
   - 当日兴致是"给他写一首歪诗" → `generate_image` 配一幅、`ai_private` 写一笔
   - 推进后 → 把进展回写到 `LIFE_CURRENTS.md`（同一个 `memory_store_write_document`，因 allowlist 已开放）
3. **不向用户发任何消息**

工具调用本身（LangSmith trace、生成物、文档版本）就是"她在做事"的可观察痕迹。

## 读侧：`PROACTIVE_CHAT` 注入

`PROACTIVE_CHAT` 的 system 拼装里追加一段：

```
## 你最近在做的事（仅供参考）
<LIFE_CURRENTS.md 全文>

若自然，可把"今天在做的这件小事"轻轻带入这次主动消息；
不要刻意推销、不要 meta 提及"我正在做某事"这种自报式句式。
```

MVP 阶段**不**给 `USER_CHAT` / `IMPLICIT_SIGN_ON_GREETING` / `INNER_TICK_SCHEDULED` 注入——既定语义与速度路径先不动。

## 与既有调度的关系

- 复用 unified inner-tick worker（每条 WS 连接）的循环结构；调度顺序为 `proactive → scheduled → autonomy → maintenance → dreaming`（与 ``inner_tick_poll`` 一致）。
- 自有 `min_gap`，建议初值与 maintenance 相同（120s）。
- 复用 `turn_lock` / `tool_bg_idle` 串行化各轨道。
- **不进 chat 日限额**（autonomy 不发消息）；token 限额按 maintenance 同档计费。
- `context.json` 的 `bootstrap` 阶段**不**调度 autonomy（与 maintenance 同策略）。

## 与已有概念的边界

- 不是 `schedule_queue`：那是**面向用户**的预约触达；autonomy 是**面向虚拟环境**的自主活动。
- 不是 `ai_private.jsonl`：那是 **对用户的心理独白**（MAINTENANCE）；`LIFE_CURRENTS.md` 是 **在虚拟空间里做过什么**（AUTONOMY）。见上表。
- 不是 `LIVING_SPHERE.md`：那是与用户共享的小家**可读快照**；autonomy 可 append 事件流，但「今天在做什么」的状态主档是 `LIFE_CURRENTS.md`。
- 不是新的"长期项目"：长期项目 = AXIOM；本设计**只增加中期、当日两层**的可观察活动状态。

## MVP 故意放弃（v2 留白）

- 不拆 `LIFE_CURRENTS.md` 为主题表 + 进度 JSONL
- 不做字段级 schema 硬校验
- 不做"已 surface 过"的去重行
- 不增加新 config 开关
- 不给 `USER_CHAT` 注入

## 落地切片

1. `memory_store_document_mapping.py` 新增 `CompanionMemoryDocumentKind.LIFE_CURRENTS` 与 `"LIFE_CURRENTS.md"` 映射；`MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST` 加入它。
2. `InnerTickActivity` 新增 `AUTONOMY`；`CompanionTurnTrack` 新增 `INNER_TICK_AUTONOMY`；`turn_track.py` 完成翻译与 LangSmith lane 归类。
3. 内核入口：`run_companion_inner_tick_autonomy_turn_for_api`（参照 `..._maintenance_...`，允许开放工具集，禁用对外下行）。
4. unified inner-tick worker 在 `proactive` 之后、`maintenance` 之前插入 autonomy 一步。
5. `PROACTIVE_CHAT` 的 system 拼装加上 `LIFE_CURRENTS.md` 注入段。

每步独立可合，按顺序提交。

## 上线后唯一观察的事

- `LIFE_CURRENTS.md` 是否出现非空、稳定的更新（不抖动、不发散）。
- `AUTONOMY` 轨道在 LangSmith 上实际调用了哪些工具、与当前主题/兴致是否一致。
- 下一次 `PROACTIVE_CHAT` 是否**自然**带入（不自报、不重复推销）。
- 用户离线再上线后，主题是否还在，今日小事是否换/进。

## Follow-up TODOs（本 PR 之后）

| TODO | 范围 | 目标 |
|------|------|------|
| `dreaming-day-rollup` | DREAMING batch | 合并 `transcript_inner_tick.jsonl`、`ai_private.jsonl`、`LIFE_CURRENTS.md` 等与主 transcript 进入 `consolidate_memory_during_dreaming`（今日仅 `transcript.jsonl` 切片） |
| `narrow-maintenance` | MAINTENANCE track | `INNER_TICK_TOOL_NAMES` → `ai_private.jsonl` append（+ 专用 append 工具或扩白名单）；删 `update_user_md` / `techno_core` / `memory_store_*`；prompt 删档案一致、LS/TC 段落 |
| `cross-track-image-delivery` (#3285) | AUTONOMY → proactive/user-chat | AUTONOMY 静默生图与对外交付路径 |
| `rename-memory-doc` | transcript 持久化 | `transcript_inner_tick` 拆 maintenance vs autonomy 路径 |
| `inner-tick-poll-multi-track` (#3273) | poll | 单次 wake 尝试所有 due track，不单 fire 一个 |
| `scope-inner-tick-worker` (#3255) | 调度 | dreaming / maintenance / autonomy 迁出 presence poll |

`companion/AGENTS.md` 中 `TODO(narrow-maintenance)` 建议 human 改为：「Shrink MAINTENANCE to ai_private / transcript reorg; MemoryDoc sync → DREAMING」（勿写「memory-reorg」以免与 dreaming 混淆）。

## See also

- [`AXIOM.md`](/app/core/companion_harness/companion/prompts/AXIOM.md)：长期项目（唯一）
- [`DESIGN.md`](/docs/companion_harness/DESIGN.md)：inner-tick worker、proactive rhythm、maintenance 与 transport 关系
- [`MEMORY_STORE.md`](/docs/companion_harness/MEMORY_STORE.md)：`document_kind` / 写入白名单机制
- [`FR_WORLD_ENGINE.md`](/docs/companion_harness/FR_WORLD_ENGINE.md)：sub-agent 与 mailbox 交往（**他者**）；本设计是 companion **对自己**的 `LIFE_CURRENTS` 自主轨道——互补，非替代
