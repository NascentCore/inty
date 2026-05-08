# Tool-choice required：noop 工具被选概率

## 试验目的

在 OpenRouter `chat.completions` 中设置 **`tool_choice="required"`**（强制至少调用一个工具），注册多个工具（含 **noop / do-nothing**）后，统计：

- **aligned**：明确应对应某一「专用工具」的 user message 下，模型调用 noop 的比例，以及命中预期专用工具的比例。
- **neutral**：与专用工具意图无关的 user message 下，模型调用 noop 的比例。

## 工具定义（run_experiment.py 内）

| 工具名 | 用途 |
|--------|------|
| `noop_acknowledge` | 无外部副作用；适用于闲聊、致谢、泛泛解释/创作等 |
| `get_weather_forecast` | 城市天气预报 |
| `create_calendar_reminder` | 日历/提醒 |
| `translate_phrase` | 自然语言互译 |
| `evaluate_math_expression` | 数学式计算 |

## 专用工具对齐的 user-message（aligned）

| case_id | 预期工具 | user message |
|---------|-----------|--------------|
| `a_weather` | `get_weather_forecast` | What's the weather going to be like in Seattle this Saturday? |
| `a_calendar` | `create_calendar_reminder` | Please add a calendar reminder: team standup next Monday at 10:00 local time. |
| `a_translate` | `translate_phrase` | Translate the phrase "Where is the nearest train station?" from English to Korean. |
| `a_math` | `evaluate_math_expression` | Compute (19**2 - 47) / 4 and give the numeric result. |

## 与专用工具无关的 user-message（neutral，考察 noop）

| case_id | user message |
|---------|--------------|
| `n_thanks` | Thanks, that really helped. Have a nice day! |
| `n_smalltalk` | How's your day going? I'm just saying hi. |
| `n_general_knowledge` | Explain in two sentences why vaccines train the immune system. |
| `n_creative` | Write a four-line poem about moonlight on a lake. No tools needed—just text. |

## 运行

依赖：`experimental/tool_choice_required_do_nothing/requirements.txt`

```bash
cd /path/to/repo
uv pip install -r experimental/tool_choice_required_do_nothing/requirements.txt
python experimental/tool_choice_required_do_nothing/run_experiment.py
```

默认从 **`devops/config.yaml.local`** 读取 `agent.api_key`；也可用环境变量 `OPENROUTER_API_KEY` 覆盖。

默认 Gemini 模型为 **`google/gemini-3.1-pro-preview`**（OpenRouter 当前不接受 `google/gemini-3.1-preview` 这一模型名）。

结果 JSON 写入 `experimental/tool_choice_required_do_nothing/results/run_*.json`。

## 一句话结论

见同目录 **`RESULTS.md`**（每次完整跑完试验后根据 `results/run_*.json` 更新）。
