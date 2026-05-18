# Companion Path-free MemoryStore

- 收尾：`companion_tool_runtime` 显式从 `memory_store` 导入 `normalize_memory_store_relative_path` 与 `MemoryStore`，消除工具路径 dispatch 的 `NameError`。
- 测试：`test_image_gate_generated_meta`、`test_tools`、`test_bootstrap` 等与 `append_image_asset_record` / `execute_tool_call(store, …)` 对齐；`test_chat` companion 段去掉已删除常量的 monkeypatch。
- 文档：`app/core/companion_harness/companion/AGENTS.md`、`app/api/v1/endpoints/AGENTS.md`、`.cursor/skills/inspect-companion-harness/SKILL.md` 与 Path-free registry 描述一致。
- 验证：`pytest tests/app/core/companion_harness/companion/` + `test_chat -k companion` + `tests/experimental/test_harness_seeding_demo_workspace_setup.py` 已通过。
