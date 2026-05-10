# 试验结果摘要

- **最新完整运行**：`results/run_20260508T052309Z.json`  
- **配置**：`tool_choice="required"`，`temperature=0.2`，每 case **8** 次重复；aligned / neutral 各 4 条 case → 每模型 **64** 次调用。  
- **Gemini 模型**：OpenRouter 上 **`google/gemini-3.1-preview` 无效**，脚本默认改为 **`google/gemini-3.1-pro-preview`**（见 `README.md`）。

## 汇总（来自 `run_20260508T052309Z.json`）

| 模型 | aligned → noop 比例 | neutral → noop 比例 | aligned 命中预期专用工具比例 |
|------|---------------------|---------------------|-------------------------------|
| `google/gemini-3.1-pro-preview` | 0/32 = **0%** | 32/32 = **100%** | 32/32 = **100%** |
| `deepseek/deepseek-v4-flash` | 0/32 = **0%** | 25/32 ≈ **78.1%** | 27/32 ≈ **84.4%** |

## 一句话结论

在强制工具调用且并存 noop 与多个专用工具时，**Gemini 3.1 Pro Preview 对「专用意图 vs 闲聊/知识/创作」路由极其稳定（中性句 100% 选 noop、对齐句 100% 选预期工具）**，而 **DeepSeek V4 Flash 在无专用意图时仍会约 22% 误选专用工具，且对齐句约 16% 未命中预期工具**。
