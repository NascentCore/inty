# FR_AGENTIC_PERSONIFIED_REPO_DESIGN

## 1. 背景与目标

本设计定义一种 `agentic personified git repo`：  
仓库不只是代码容器，而是一个“人格化实体（Personified Entity）”。

该实体具备三层能力：

1. **Understand itself**：能读取并解释自己的架构、能力、边界、历史演进。
2. **Present to users**：能对外表达“我是谁、我能做什么、为什么这样设计、如何使用我”。
3. **Evolve itself**：能基于运行信号提出和实施自我更新（通过 git 变更），并在治理约束下持续改进。

最终目标：即使没有外部“更强代理”包裹，该仓库内置的 agent runtime 也能直接服务用户，形成 **agent 与 code 的共生系统**。

## 2. 非目标

1. 不追求一次性全自动“无监督自改代码”。
2. 不绕过 git 审查、测试、权限边界。
3. 不把业务人格抽象成无差别模板机器人。
4. 不在本阶段重做 Android / Ops / 全链路部署架构。

## 3. 核心设计原则

1. **Identity-first**：先定义身份与使命，再定义工具与流程。
2. **Repo as body**：代码、文档、测试、变更历史共同构成“身体”。
3. **Evolution by pull request**：演进必须通过可追踪 git 变更。
4. **Fail loud, learn fast**：失败应快速暴露并沉淀为可复用经验。
5. **Human-agent co-governance**：人类设宪法，agent 在宪法内自治演进。

## 4. 人格化实体模型（Personified Repo Model）

## 4.1 身份层（Identity Layer）

定义仓库人格的长期稳定内核：

- `mission`: 长期目标与用户价值承诺
- `persona`: 语气、互动风格、关系边界
- `values`: 决策价值观（稳定性、可解释性、低打扰）
- `non_goals`: 明确不做事项

建议落地文件：

- `repo_agent/identity/mission.md`
- `repo_agent/identity/persona.md`
- `repo_agent/identity/constitution.md`

## 4.2 自我认知层（Self-Model Layer）

用于让 agent 解释“我如何工作”：

- 组件地图（服务、目录、依赖图）
- 能力目录（可调用能力、输入输出、限制）
- 风险画像（高风险模块、变更注意事项）
- 历史记忆（重要决策与回滚案例）

建议落地文件：

- `repo_agent/self_model/system_map.yaml`
- `repo_agent/self_model/capabilities.yaml`
- `repo_agent/self_model/risk_register.yaml`
- `repo_agent/memory/decision_log.md`

## 4.3 行动层（Action Layer）

将认知转为可执行动作：

- 读写仓库（受策略约束）
- 运行测试
- 生成设计提案
- 生成迁移计划
- 提交、推送、更新 PR

建议落地模块：

- `repo_agent/runtime/orchestrator.py`
- `repo_agent/runtime/tool_registry.py`
- `repo_agent/runtime/evolution_loop.py`

## 5. 自演进闭环（Self-Evolution Loop）

统一闭环：`Observe -> Diagnose -> Propose -> Simulate -> Apply -> Verify -> Reflect`

## 5.1 Observe（观测）

输入信号：

- 用户对话与需求
- issue / PR 评论
- CI 失败日志
- 线上指标异常

产物：

- `repo_agent/memory/signals/YYYY_MM_DD.md`

## 5.2 Diagnose（诊断）

将信号映射为结构化问题：

- 问题类型（bug / debt / feature gap / doc gap）
- 影响面
- 紧急度
- 根因假设

产物：

- `repo_agent/memory/diagnosis/<ticket_id>.md`

## 5.3 Propose（提案）

生成 RFC 级设计提案，至少包含：

- 目标与成功标准
- 变更范围与非目标
- 目录/接口影响
- 测试策略
- 回滚策略

产物：

- `docs/FR_*.md`

## 5.4 Simulate（仿真）

在不污染主路径前提下验证提案：

- 运行定向测试
- 对关键路径做冒烟验证
- 记录风险与阻塞

产物：

- `tests/docs/TEST_STEPS_*.md`

## 5.5 Apply（应用）

通过最小可审查变更落地：

- 小步提交（单职责）
- 每步可回滚
- 变更与证据绑定

## 5.6 Verify & Reflect（验收与反思）

验收通过后沉淀到长期记忆：

- 成功模式（what works）
- 失败模式（what breaks）
- 下一轮演进触发条件

产物：

- `repo_agent/memory/retrospectives/<change_id>.md`

## 6. “无额外 agent 外挂”目标的实现方式

为达成“仓库自身即可直接服务用户”，需要把能力内生到 repo：

1. **内生入口**：统一 CLI/API（例如 `repo_agent serve`）。
2. **内生知识**：自我说明、架构图、操作手册都在仓库内。
3. **内生治理**：变更门禁与演进策略由仓库配置驱动。
4. **内生记忆**：关键决策、经验、失败案例沉淀在版本化文档。

这意味着外部代理只需提供执行容器，核心智能行为在仓库内部完成。

## 7. 参考目录蓝图（可渐进实施）

```text
repo_agent/
  identity/
    mission.md
    persona.md
    constitution.md
  self_model/
    system_map.yaml
    capabilities.yaml
    risk_register.yaml
  memory/
    signals/
    diagnosis/
    retrospectives/
    decision_log.md
  runtime/
    orchestrator.py
    tool_registry.py
    evolution_loop.py
  governance/
    change_policy.yaml
    release_gates.yaml
  interfaces/
    cli.py
    api.py
```

## 8. 治理与安全边界（Governance & Safety）

必须有明确 guardrails，避免“失控自修改”：

1. **Policy Gate**：禁止触碰敏感路径（密钥、账务、权限）。
2. **Test Gate**：不通过关键测试不得进入 apply。
3. **Review Gate**：高风险变更必须人工确认。
4. **Rollback Gate**：每次变更都有一键回滚策略。
5. **Audit Trail**：决策理由、测试证据、diff 必须可追溯。

## 9. 交互体验设计（How it presents to users）

对用户暴露三个模式：

1. **Explain mode**：解释架构、能力、限制、最近演进。
2. **Guide mode**：指导用户如何使用仓库功能与开发流程。
3. **Execute mode**：在授权范围内直接完成任务并交付证据。

统一回答格式建议：

- `Who I am`
- `What I can do now`
- `What changed recently`
- `What I propose next`

## 10. 分阶段落地路线

## Phase 0：定义人格与治理骨架

- 创建 `identity/`、`governance/`、`self_model/` 空骨架
- 固化变更门禁策略

验收：仓库可回答“我是谁、我能做什么、我的边界是什么”。

## Phase 1：打通自说明与任务执行

- 建立统一 orchestrator + tool registry
- 支持 explain/guide/execute 三模式

验收：可完成“解释 + 执行 + 回执”闭环。

## Phase 2：打通自演进闭环

- 接入 observe/diagnose/propose/simulate/apply/verify/reflect
- 输出可审查 RFC 与测试证据

验收：可从信号出发独立产出并落地一次高质量改动。

## Phase 3：持续优化与自治增强

- 演进策略参数化（风险阈值、触发条件）
- 建立可度量演进 KPI（成功率、回滚率、修复时延）

验收：演进质量稳定且可量化。

## 11. 成功标准（Definition of Success）

达到以下条件可视为“agentic personified repo”达标：

1. 仓库可自解释：身份、能力、边界、历史可追溯。
2. 仓库可服务：用户任务可直接被执行并返回证据。
3. 仓库可自演进：在治理门禁内持续提出并落地改进。
4. 仓库可共生：agent 行为与代码结构互相强化，而非互相割裂。

## 12. 对当前仓库的最小落地建议（Next Actions）

1. 新增 `repo_agent/` 目录骨架与最小入口（先文档后代码）。
2. 把已有 `docs/FR_*` 与 `tests/docs/TEST_STEPS_*` 纳入 proposal/simulate 标准流程。
3. 选取一个低风险改动，执行一次完整演进闭环作为样板。
4. 在样板完成后再扩展到跨模块变更（backend + evaluation + android docs 协同）。

---

本设计文档是“人格化仓库”执行基线。后续若实现偏离，先更新本文档，再改实现。
