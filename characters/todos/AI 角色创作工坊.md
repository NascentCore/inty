# 如何用 AI 生成角色创意并进行延伸

- [ ] 总结现有场景

---

## 重构思路点评（run_dify_chat.py 角色模版 + 故事线）

### 目标概述

1. **角色模版**：从当前「name + 一句 description」升级为结构化模版，维度包括身份生理（性别、出生日期、种族+人口占比、国籍+2025 人口）、家庭背景、体型（肤色、身高、三围）、成长经历、目前社会状态（工作、婚育等），以及 TODO 扩展。
2. **故事线**：多个默认故事线梗概（按剧情倾向演绎、不设计具体故事以免变成 role play）；为每个用户随机选故事线；默认展示：intro → first encounter → 为 first encounter 生成开场白。

### 优点

- 模版维度清晰，便于扩展与后续推荐/筛选；人种/国籍+人口数据可用于多样性权重或抽样。
- 故事线「梗概 + 倾向」能提高多样性，又用「不写死具体剧情」避免纯 role play，边界合理；intro → first encounter → opening 与产品动线一致。

### 需要先厘清的点

**角色模版**

- **谁消费**：当前链路是 OpenRouter → 脚本（name + description）→ Dify inputs → 后端/DB。模版中种族、国籍、三围、婚育等若只作「生成时的约束」、不落库不展示则实现简单、合规压力小；若要落库或展示，需与 Agent 表 / Dify inputs / 前端 schema 对齐，并考虑哪些进 `meta_data`、是否要做检索。
- **敏感与合规**：种族、体型（尤其三围）在美国语境下易涉及歧视/body shaming；建议模版先作「生成阶段控制变量」，对外只暴露安全摘要（如 intro / first encounter 文案）。
- 人种/人口数据：若仅用于控制生成分布（如按人口比例抽样）没问题；若在 UI 展示「该人种占世界 x%」需明确产品价值与合规。

**故事线**

- **「剧情倾向」可操作化**：建议列 5–10 个倾向枚举（如浪漫/冲突/职场/家庭/成长），并约定每个角色/每次生成如何选（随机 vs 按比例）。
- **first encounter 与 opening 谁生成**：若在脚本里则需多次调 OpenRouter，延迟与成本上升；若在 Dify 工作流里根据「角色模版 + 故事线 id」生成，则脚本只负责造角色并传参，更符合现有架构。
- **与现有字段对应**：Agent 已有 `intro`、`opening`，无单独 first encounter 字段；需约定 first encounter 是 intro 的一段、还是新字段、或仅 Dify 中间变量。

### 实现顺序建议

1. **先做「角色模版」可执行版**：在 `prompt_template.py` 增加模版 prompt（1.1–1.5），扩展 `GeneratedCharacter` 与 OpenRouter json_schema；脚本中把生成结果**只映射到当前 Dify/后端已有字段**（name、description、intro），暂不新增 DB 列或 Dify 输入；验证模版能否带来更多样、可控的角色。
   - [ ] 测试角色三视图是否能改善消息生图的质量
     
     <img width="600" height="1296" alt="image" src="https://github.com/user-attachments/assets/769e66ac-a2ca-494d-9d44-2e83195242e7" />
3. **再定故事线数据结构**：例如若干条「故事线梗概 + 剧情倾向」配置；每个角色生成时随机选一条，把 story_line_id 或倾向传给 Dify；由 Dify 用这些变量生成 first encounter 与 opening。
4. **最后再考虑**：人种/国籍等统计数据的注入方式；「为每个用户随机选故事线」是在角色创建时固定，还是用户首次进入时再选（后者需用户–角色–故事线绑定与存储）。

### 与现有代码的对接

- `build_dify_payload` 目前只传 name、description；若增加 intro / first_encounter / opening，需 Dify 工作流先支持对应 inputs，再在脚本里扩展 payload。
- Agent 表已有 intro、opening、meta_data；若模版部分落库，优先用 `meta_data` 或现有 JSON 列，避免一上来改表。
- 脚本约定（tools/scripts/AGENTS.md）：幂等、参数化、dry-run/确认；若 OpenRouter 调用次数增加，建议加 `--dry-run` 与可选 `--skip-dify`，只生成不提交便于调试。
