# LLM 上下文独立指令容量总结

- 运行 ID: `20260330T110255Z`
- 生成时间(UTC): `2026-03-30T11:03:51.505325+00:00`
- 模型: `deepseek/deepseek-v3.2`
- 是否 dry-run: `True`
- 每个单元试验次数: `10`

## 阈值

- IA >= 0.95
- RSR >= 0.85
- 有效性 >= 0.92
- 格式错误率 <= 0.02

## 上限建议

- <=8: U_rec=None, U_hard=0.25
- <=16: U_rec=None, U_hard=0.25
- <=32: U_rec=None, U_hard=0.25
- <=64: U_rec=None, U_hard=0.25

