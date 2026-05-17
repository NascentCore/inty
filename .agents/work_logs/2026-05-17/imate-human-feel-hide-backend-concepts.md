# iMate 人感：用户可见层须包装 harness 后台概念

王琢誉（2026-05-17，飞书）：imate 人感打造中，**隐藏**很重要；对用户暴露 memory、tools 调用、runtime 等会直接显得是机器，后台概念必须包装。

## 记录位置

- 偏好已写入 [USERS.md](../../USERS.md) → 王琢誉 / iMate 人感 · 隐藏后台概念。

## 后续待办（编码/产品协作）

- 与琢誉对齐 **用户可见语汇 ↔ 内部概念** 对照（可进 `guidelines/TERMINOLOGY.md` 的用户向小节，仅写意图不写实现）。
- 审计 iMate Android/iOS：**加载态、错误、设置、反馈** 等是否泄漏 harness 词；REPL/Ops 保持技术词、客户端严格分层。
- 新功能/新状态 PR：默认过一遍 **copy review**（是否仍像「系统在跑管线」）。
