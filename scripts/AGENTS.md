# AGENTS.md · scripts/（脚本）

- 最简设计来完成用户需求
- **节日记忆摘要（离线）**：`apply_festival_summary_to_chats_json.py` 对 `query_chat_history_by_date.py --include-messages` 导出的 chats.json 应用与线上一致的节日记忆摘要逻辑，输出带 `festival_summary` 的 JSON。选项：`--input-json`/`-i`、`--output-json`/`-o`、`--festival-name`、`--festival-date`（可选）、`--prompt`/`--prompt-file`、`--limit`、`--dry-run`。运行前需 config.yaml 在 cwd。
- 使用 [cyclopts](https://github.com/BrianPugh/cyclopts) 来实现命令行界面
- 脚本需可重复执行（幂等），参数化（使用 `argparse`/配置），日志使用 `logger.debug()`。
- 依赖在本目录 `requirements.txt` 中声明；禁止隐式外部依赖。
- 修改数据的脚本需具备 Dry-Run 与明确确认机制。
- 在代码库顶层目录 `export PYTHONPATH=.` 不要在 python 代码中添加设置引用路径的代码
- `app/models/agent.py` 中的 Agent 表中的 readable_id 字段已被废弃，不要再使用
- `scripts/requirements.txt` 中的依赖不要添加版本约束
