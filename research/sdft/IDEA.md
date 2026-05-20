# SDFT 复现：意图与边界

## Scope

复现 [Self-Distillation Enables Continual Learning](https://arxiv.org/abs/2601.19897) 中的 **Self-Distillation Fine-Tuning (SDFT)**：用 demonstration-conditioned 的同一模型作 teacher，在 student on-policy 轨迹上做蒸馏，相对 off-policy SFT 减轻灾难性遗忘。

本目录 **不** 实现训练内核；算法与数据格式化以 [官方仓库](https://github.com/idanshen/Self-Distillation) 为准。

## 与 Inty 的关系（探索性）

长期伴侣可能需要从演示中持续学技能且不伤既有能力；SDFT 是「仅演示、无 reward」的 on-policy 路径，当前与 companion harness 无直接耦合。
长期可能用于优化 toocall 模型的工具调用准确度、效率，或其他能力指标。

## 本 PR 范围

- P0：脚手架、upstream pin、smoke 配置、CPU 降级验收。
- P1：`tooluse` / `science` 配置与 eval 子进程包装。
- **不在此 PR**：SFT baseline、顺序三任务、lm_eval 遗忘、云 GPU 端到端（见 README Follow-up）。

## 论文 vs 官方代码

- 论文表述 reverse KL；**官方默认** on-policy + forward KL（`DistilConfig.alpha=0.0`）。复现以 pinned upstream 为准。
