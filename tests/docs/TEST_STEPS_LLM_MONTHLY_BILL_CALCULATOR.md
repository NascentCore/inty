# TEST_STEPS_LLM_MONTHLY_BILL_CALCULATOR

## 目标

验证 `tools/scripts/calculate_llm_monthly_bill.py` 可以：

1. 手动录入模型定价（每个模型有唯一标识）
2. 在计算阶段按“先输入用量，再选择模型”的流程执行
3. 一次选择 1 个或多个模型并输出分项费用与总费用

## 前置条件

- 在仓库根目录执行
- 运行前设置：

```bash
export PYTHONPATH=.
```

## 用例 1：全参数模式（便于自动化验证）

```bash
python tools/scripts/calculate_llm_monthly_bill.py \
  --model-pricing "gpt-4o-mini,0.15,0.60,0.075,0.30" \
  --model-pricing "gemini-2.5-flash,0.10,0.40,0.05,0.20" \
  --usage-input-tokens 2000000 \
  --usage-output-tokens 1000000 \
  --usage-cache-read-tokens 500000 \
  --usage-cache-write-tokens 200000 \
  --select-model gpt-4o-mini \
  --select-model gemini-2.5-flash
```

预期：
- 输出两个模型的输入/输出/缓存读/缓存写费用与总费用
- 结果为：
  - `gpt-4o-mini` 总费用 = `0.997500` USD
  - `gemini-2.5-flash` 总费用 = `0.665000` USD

## 用例 2：交互模式（验证流程顺序）

```bash
printf "gpt-4o-mini,0.15,0.60,0.075,0.30\ngemini-2.5-flash,0.10,0.40,0.05,0.20\n\n2000000\n1000000\n500000\n200000\ngpt-4o-mini,gemini-2.5-flash\n" | \
python tools/scripts/calculate_llm_monthly_bill.py
```

预期：
- 出现“步骤 1/2：输入月度用量数据（token）”
- 随后出现“步骤 2/2：选择参与计算的模型（可多选）”
- 输出两个模型的账单明细
