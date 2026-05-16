# User preferences

**Users' general preferences, not specific to individuals.**

- **不做防御式编程**：不要为「万一」加可选分支、吞错、静默降级或多余 try/except；与仓库 `AGENTS.md` 里「不臆造旋钮 / 不过度防御」一致。**灾难性前提缺失**（缺文件、空种子模板、不可恢复的配置）应在清晰边界上**尽快硬失败**（如 `FileNotFoundError`、对不变量的 `assert`），而不是打日志后继续跑。
- **避免组合爆炸的内部机制**：不要堆叠多个独立 on/off、`*_every_n`、条件门控等，让运行时状态呈 \(2^k\) 级组合却无人实际配置（例：记忆管线曾有的 `*_disabled` + 分文档 `*_every_n` + SOUL 信号/ bootstrap lock）。默认一条清晰路径；真需要调参时只加**用户会用的**、**已验证需要**的单一旋钮。
- Companion WebSocket：**产品约定**隐式问候用 **`user_signed_on` + `implicit_greeting` + `message_id`**；不在服务端对 **`IMPLICIT_USER_SIGNED_ON`** 聊天帧做 wire 预拒绝（与内部 synthetic 一致）。

## 人类队友（Human Partners）

### 赵亚雄/yxzhao6

- Companion Harness 开发者，Inty 构思者，1984 年出生，计算机科学博士，14 年专业工作经验（Amazon、Google、AI startups）
- 对代码理解深刻
- 记忆管线等 harness 配置：**从未用过**细粒度开关；倾向删掉未使用的组合式配置，而非继续维护。

### 王琢誉/wangz233

- 产品经理，本科学历，6 年工作经验，多款 AIGC、AI 陪伴产品经验
- 评价产品体验
