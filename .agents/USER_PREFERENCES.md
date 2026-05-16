# User preferences

**Users' general preferences, not specific to individuals.**

- **不做防御式编程**：不要为「万一」加可选分支、吞错、静默降级或多余 try/except；与仓库 `AGENTS.md` 里「不臆造旋钮 / 不过度防御」一致。**灾难性前提缺失**（缺文件、空种子模板、不可恢复的配置）应在清晰边界上**尽快硬失败**（如 `FileNotFoundError`、对不变量的 `assert`），而不是打日志后继续跑。
- Companion WebSocket 问候：`user_signed_on` **必须**带 RFC4122 **`message_id`**，缺则 ack 失败。
