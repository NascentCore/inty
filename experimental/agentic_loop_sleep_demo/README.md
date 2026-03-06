# Agentic Loop Sleep Demo（无错误处理版）

这个 demo 的目标只有一个：  
**用最小代码展示 agentic loop 的底层机制**，即：

1. LLM 读上下文并决定是否调用工具
2. 框架执行工具（这里是 `sleep`）
3. 工具结果写回消息上下文
4. 控制权回到 LLM，进入下一轮 loop

---

## 为什么这个 demo 故意“很裸”

为了教学清晰度，这份代码刻意做了以下取舍：

- 不做任何 error handling（没有 `try/except`）
- 只演示一个工具：`sleep`
- 工具参数极简，只保留 `reason`
- sleep 秒数由工具从上下文里读取（最后一条用户消息中的第一个整数）

这样读者可以把注意力集中在 loop 机制本身，而不是工程化细节。

---

## 目录结构

- `main.py`：完整可运行示例（CLI + loop + tool 执行）
- `__init__.py`：空文件，仅声明包

---

## 运行前准备

在项目根目录创建 `.env`，放入 OpenRouter key（或你自己的 OpenAI-compatible key）：

```bash
OPENROUTER_API_KEY=你的key
```

本 demo 读取环境变量用的是 `python-dotenv`，会自动加载根目录 `.env`。

---

## 一条命令运行

在仓库根目录执行：

```bash
python -m experimental.agentic_loop_sleep_demo.main \
  --user-request "请先 sleep 3 秒，然后告诉我你回来了" \
  --model "z-ai/glm-4.5-air:free"
```

---

## 你会看到的关键日志

典型输出结构如下（示意）：

1. `Loop Step 1`：LLM 返回了 `tool_calls=[sleep(...)]`
2. 程序执行 `sleep` 工具，阻塞等待 N 秒
3. 工具结果以 `role=tool` 写回 `messages`
4. `Loop Step 2`：LLM 读取工具结果后输出最终文本回复
5. loop 结束

---

## 代码阅读建议（按顺序）

1. `run_agentic_loop(...)`  
   先看主循环结构，理解“何时继续 loop、何时结束”。

2. `_execute_sleep_tool(...)`  
   再看工具执行层，理解“工具如何读取上下文并返回结构化结果”。

3. `_extract_sleep_seconds_from_context(...)`  
   最后看“上下文 -> 工具行为”的最小映射逻辑。

---

## 这个 demo 没做什么（故意不做）

- 没有参数校验
- 没有异常恢复
- 没有重试
- 没有并行工具调用
- 没有 memory / planning / reflection

这些都属于下一层工程化主题，不是这份教学 demo 的重点。

