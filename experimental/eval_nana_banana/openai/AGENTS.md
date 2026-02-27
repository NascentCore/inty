# 评测 OpenAI Images Edit（gpt-image-1.5）

- **lib.py**：封装 OpenAI 官方 SDK 的 `client.images.edit()`（多图 + prompt → 编辑图），与 `save_result_to_files`（将 base64 解码写图并写 JSON）。输入为本地角色/用户头像路径，SDK 支持多图（本脚本传 2 张）。输出路径：`output_dir/openai/<model>/`，与 Fal 的 `tmp/fal-ai/...` 不冲突。
- **eval_prod_failed_prompts.py**：对 `tmp/scene_prompt_*.txt` 逐条读 prompt，用默认角色/用户头像路径调用 OpenAI Images Edit 生成并落盘。成功时图片与 JSON 写入 `output_dir/openai/<model>/`；若某条触发 API 报错（如 content policy、超时）：打印异常、将完整错误写入同目录下 `{files_prefix}_openai_output_{timestamp}_error.json`，然后继续下一条。示例：`python -m experimental.eval_nana_banana.openai.eval_prod_failed_prompts --model gpt-image-1.5`。认证使用环境变量 `OPENAI_API_KEY`（如通过 .env 由 load_dotenv 加载）。
