# LLM 上下文指令容量总结

- 运行 ID：`20260330T162012Z`
- 生成时间（UTC）：`2026-03-30T16:29:44.517299+00:00`
- 模型：`openai/gpt-4o-mini`
- 是否 dry-run：`False`
- 每个单元试验次数：`3`

## 阈值

- IA >= 0.95
- RSR >= 0.85
- 有效性 >= 0.92
- 格式错误率 <= 0.02

## 上限建议

- <=8: U_rec=None, U_hard=0.55
- <=16: U_rec=None, U_hard=0.55
- <=32: U_rec=None, U_hard=None
- <=64: U_rec=None, U_hard=None

