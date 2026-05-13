# Companion Harness session state: concept design and naming

持久会话状态（代码里大量称 `workspace`）在概念上拆成 **绑定键**、**版本化语料** 与 **按耐久契约划分的协同态**；**不把可选磁盘挂载当作范式必备项**（生产权威在 repository / DB；本地 REPL 不再作为 companion 运行面时尤其如此）。

## 1. 问题与目标

- **语义混杂**：`workspace` 同时暗示 IDE 工程目录、用户本机路径、DB 分区与进程内队列。
- **单靠分层盒子不够**：同一 artifact 是「模型真理」还是「侧车协同」，应由 **重启后与权威来源的契约** 决定，而非是否长得像文件。
- **命名避免**：不以 `Ledger`（复式账本联想）、笼统 `Runtime`（语言运行时 / 掩盖落盘）作为主轴术语。

## 2. 原则（第一性）

1. **分区键先于存储形态**：一切状态都能回答「属于哪一段长期陪伴会话」。
2. **真理按耐久契约分级**：允许丢失与否、以 DB 还是以本地为准，写清后再归类。
3. **语料默认版本化读 head**：按键追加版本、读当前 head；完整 history 是否暴露由产品决定，命名不预设审计形态。
4. **`corpus_rel_key` 是逻辑键**：实现可继续用相对路径符号与内部 `Path`，类型边界标明「语料键非任意 OS 路径」即可。
5. **内核词汇可泛化**：标识符优先 `Session*`；「Companion」留在模块与产品层。

## 3. 核心命名表

| 概念 | 英文名 | 含义 |
|------|--------|------|
| 会话分区键 | `SessionBinding` | 稳定三元组 `(user_id, companion_id, chat_id)`；标识长期会话分区。**不等于**单次 HTTP / 单轮 tool。与现有 `CompanionScope` 同构，可并存为别名。 |
| 版本化正文集合 | `SessionCorpus` | 某 binding 下按 `corpus_rel_key` 存储、读 head 的正文与快照（IDENTITY / SOUL / USER / MEMORY、transcript、context_json、memory 树等）。对应实现面主要是 `MemoryStore` + `companion_workspace_document_versions`。 |
| 逻辑寻址 | `corpus_rel_key` | 如 `IDENTITY.md`、`memory/daily/YYYY-MM-DD.md`；映射到 ORM 见 `/app/core/companion_harness/memory/memory_store_document_mapping.py`。 |
| 耐久协同态 | `DurableSidecar` | 一般不拼进默认 system，但 **重启后仍应有意义**；存放处与回放规则须在契约中写明。 |
| 进程私有态 | `ProcessPrivate` | 仅进程内便利；**可随进程结束丢弃或可重建**。 |

## 4. 分层（按契约，而非按是否像文件）

```
SessionBinding
├── SessionCorpus       # 人设与记忆等「当前世界」正文（读 head）
├── DurableSidecar      # 调度意图等耐久协同（介质可为 DB / KV / 遗留文件，契约为准）
└── ProcessPrivate      # 缓存、短时锁、可重建队列等
```

灰区条目：先回答「重启后用户是否应看到接续的世界？」「恢复以谁为准？」再归入上三类。

## 5. 与 Companion Harness 的关系

- **Companion Harness**：编排、工具循环、prompt 顺序；消费当前 binding 下的 **corpus head** 与（只读）必要的 sidecar 视图。
- **包内固定文案**（如 `/app/core/companion_harness/system_hierarchy/prompts/AXIOM.md`）：**不属于** `SessionCorpus`，与语料并列，避免「凡是 md 都是语料」。

## 6. 工具与迁移话术

- 模型可见工具宜逐步对齐 **`session_corpus_read` / `session_corpus_write`**，或在保留旧名的 schema 描述中固定声明「语料键，非用户设备文件系统」。
- 配置项如 `workspaces_base_dir`：若仅剩兼容或测试，宜标为 **legacy**，最终语义由 **SessionBinding + SessionCorpus** 表达。

## 7. 关于磁盘路径（非范式核心）

- **不作为概念支柱**：权威在 DB 时 **不存在**「语料必须在 disk 上的根」。
- **遗留实现**：若仍有 `Path` 用于 registry、校验或测试临时目录，视为 **adapter / harness**，不写入对外架构词汇表。
- **`tools/inty_v2_repl`**：不再作为 Companion Harness 运行面时，**更少理由**在范式层保留「挂载目录」一词；剩余磁盘用途仅限可选 spill 或过渡代码路径。

## 8. 与现存代码语的对照（便于检索）

| 现行口语 / 代码倾向 | 范式术语 |
|---------------------|----------|
| `workspace` / `workspace_path` | 实现泄漏；目标语义拆成 Binding + Corpus (+ Sidecar) |
| `workspace_root`（MemoryStore） | Corpus 访问上下文的遗留挂载或逻辑根；长期可向 binding 键收敛 |
| `CompanionScope` | `SessionBinding` 同构 |
