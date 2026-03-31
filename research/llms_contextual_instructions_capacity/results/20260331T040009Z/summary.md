# LLM 上下文指令容量摘要

- 运行 ID: `20260331T040009Z`
- 生成时间(UTC): `2026-03-31T04:19:00.656890+00:00`
- 模型: `google/gemini-2.5-flash-lite`
- dry_run: `False`
- 每个单元试验次数: `30`

## 阈值

- IA >= 0.95
- RSR >= 0.85
- 有效性（Effectiveness） >= 0.92
- 格式错误率 <= 0.02

## 严格口径上限建议（strict）

- <=8: U_rec=None, U_hard=None
- <=16: U_rec=None, U_hard=0.25
- <=32: U_rec=None, U_hard=None
- <=64: U_rec=None, U_hard=None

## 语义口径上限建议（semantic，先剥离代码块）

- <=8: U_rec=None, U_hard=None
- <=16: U_rec=None, U_hard=0.25
- <=32: U_rec=None, U_hard=None
- <=64: U_rec=None, U_hard=None

