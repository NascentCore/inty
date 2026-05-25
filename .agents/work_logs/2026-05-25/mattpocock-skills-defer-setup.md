# mattpocock/skills：暂不运行 setup-matt-pocock-skills，先试用

人类队友（2026-05-25）：已安装 [mattpocock/skills](https://github.com/mattpocock/skills)，但 **暂不** 运行 `/setup-matt-pocock-skills`；要先在实际工作中试用这些 skill，再决定是否配置 per-repo 上下文。

## 当前状态

- 14 个 skill 位于 `.agents/skills/`；版本锁定见根目录 `skills-lock.json`。
- Inty 自有 skill 仍在 `.cursor/skills/`，未改动。
- `docs/agents/` **尚未创建**（issue tracker、triage labels、domain docs 均未配置）。

## 可直接试用的 skill

- Productivity：`grill-me`、`caveman`、`handoff`、`write-a-skill`
- Engineering（不依赖 `docs/agents/`）：`grill-with-docs`、`prototype`、`zoom-out`（后者读代码为主；无 `CONTEXT.md` 时效果受限）

## 暂缺本仓库上下文的 skill

在未 setup 前，以下 skill 缺少 issue tracker / triage label / domain doc 配置，**不要假设**已有 `docs/agents/*.md`：

- `to-issues`、`to-prd`、`triage`
- `diagnose`、`tdd`、`improve-codebase-architecture`（期望 `CONTEXT.md` 与 `docs/adr/`）

## 后续待办

- 试用满意后，在 Cursor 中运行 `/setup-matt-pocock-skills`，生成 `docs/agents/` 并在 `AGENTS.md` 补全 Issue tracker / Triage labels / Domain docs 小节。
- 更新 skill：`npx skills update`
