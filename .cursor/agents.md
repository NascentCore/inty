# Project agent skills（本地，不同步 GitHub）

<!-- Generated entirely by Cursor Cloud Agent for skills → agents migration. -->

Inty 在仓库内维护 Agent Skills，供 Cursor / Cloud Agent 从目录发现 `SKILL.md`，**不**通过 Remote Rule 或 `npx skills update` 从 GitHub 拉取。

## 目录

- **Inty 自有**：`.cursor/skills/`（运维、REPL 回归、companion harness 排障等）
- **第三方 vendored**：`.agents/skills/`（自 mattpocock/skills 拷贝并随仓库演进；见 `agents-lock.json` 内容哈希，**非** upstream 同步）

## 锁文件

- 使用根目录 **`agents-lock.json`**（`sourceType: local`）记录 vendored skill 的内容指纹，便于 diff 与 review。
- 已弃用 **`skills-lock.json`**（曾指向 `mattpocock/skills` GitHub 源）。

## 维护约定

- 需要改第三方 skill 时，直接编辑 `.agents/skills/<name>/` 并更新 `agents-lock.json` 中对应 `computedHash`（或重跑仓库内生成脚本）。
- 不要对 mattpocock/skills 运行 `npx skills add` / `npx skills update`，以免重新引入 GitHub 同步元数据。
