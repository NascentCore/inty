# chat_image_gen_fallbacks_only_include_ai_character

脚本集：为「仅含一个角色」的聊天生图打标 `only_include_ai_character=True`，用作生图失败时的兜底候选。

- **check_chat_images_character_count.py**：用 Gemini 统计图中角色数，输出带 `one_character` 的 JSON。
- **tag_only_include_ai_character_from_json.py**：按 JSON 中 `one_character=true` 条目更新 Resource.resource_metadata。
- **verify_only_include_ai_character_fallback.py**：手动校验某 Resource 是否出现在 `get_generated_images_for_agent(..., only_include_ai_character=True)` 结果中。

测试步骤见 [TEST_STEPS.md](TEST_STEPS.md)。从仓库根目录运行且 `export PYTHONPATH=.`。
