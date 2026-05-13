# AGENTS.md · tools/scripts/（脚本）

- 最简设计来完成用户需求
- 使用 [cyclopts](https://github.com/BrianPugh/cyclopts) 来实现命令行界面
- 脚本需可重复执行（幂等），参数化（使用 `argparse`/配置），日志使用 `logger.debug()`。
- 依赖在本目录 `requirements.txt` 中声明；禁止隐式外部依赖。
- 修改数据的脚本需具备 Dry-Run 与明确确认机制。
- 在代码库顶层目录 `export PYTHONPATH=.` 不要在 python 代码中添加设置引用路径的代码
- `app/models/agent.py` 中的 Agent 表中的 readable_id 字段已被废弃，不要再使用
- `tools/scripts/requirements.txt` 中的依赖不要添加版本约束
- Agent 单条导出/导入：`export_agent_to_json.py` 按 id 导出完整 agent 行为 JSON；`import_agent_from_json.py` 读取该 JSON 插入 DB，默认 dry-run，需 `--no-dry-run` 与 `--yes` 或交互确认后执行
