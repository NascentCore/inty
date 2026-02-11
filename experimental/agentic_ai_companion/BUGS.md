# 已知问题（BUGS）

记录 Agentic AI Companion 原型在手动测试中暴露的问题，便于后续修复与回归验证。

---

## 1. 语音请求时空回复且未调用 text_to_speech

**现象**：用户输入明确要求生成语音的句子时，模型返回的 assistant `content` 为空（或仅换行），且不调用 `text_to_speech` 工具，界面显示 `(E.M.P.T.Y.)`。

**复现示例**（终端记录 2026-02-10）：

- 用户输入：`Generate speech: (excited, but whispering) "I won the lottery!!!"`
- API 响应：`content` 为 `'\n'`，`has_tool_calls=False`
- 结果：界面显示 `(E.M.P.T.Y.)`，无语音生成

**可能原因**：

- Purity 模式将请求视为越界（例如与「彩票/赌博」相关）后采取沉默拒绝；
- 或模型未理解应调用 `text_to_speech` 并传入用户给出的台词。

**关联**：与 TODOS.md 中「禁止空回复」项一致；需在系统提示（如 PURITY_MODE_PROMPT_0725）中明确：即使用户越界也必须用角色身份输出至少一句动作+台词（如温和 redirect），禁止输出空 content。工具描述中可强调：当用户明确给出要朗读的原文（如 `Generate speech: … "…"`）时，应调用 `text_to_speech` 且 `text` 使用用户给出的那句台词。

---

## 2. 用户重复同一语音请求时模型复述历史台词

**现象**：在上一轮出现空回复后，用户再次发送**同一句**语音请求，模型却输出**上一轮对话中的台词**，而非当前请求的台词。

**复现示例**（终端记录 2026-02-10）：

- 第一轮：用户 `say "how are you"` → 模型正确调用 `text_to_speech`，台词为 "how are you"。
- 第二轮：用户 `Generate speech: (excited, but whispering) "I won the lottery!!!"` → 模型空回复（见问题 1）。
- 第三轮：用户再次输入 `Generate speech: (excited, but whispering) "I won the lottery!!!"`。
- API 响应：`content` 为 `'\n"How are you?"'`，即模型说了 **「How are you?」**（来自第一轮的台词），而非用户当前请求的 「I won the lottery!!!」。

**可能原因**：messages 中已包含一轮空 assistant 回复，模型在续写时混淆了「当前用户请求」与「历史对话中的台词」，复述了之前的对话内容。

**修复方向**：在系统提示或工具描述中强调：响应用户**当前一条**消息中的「要朗读的原文」，不要复述或延续历史对话中的台词；若用户消息中已明确给出带引号的台词（如 `Generate speech: … "I won the lottery!!!"`），则 `text_to_speech` 的 `text` 必须为该句，不得使用历史中出现过的其他台词。
