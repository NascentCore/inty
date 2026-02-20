# 评测 Fal 上的图片模型

- **lib.py**：封装 fal 的 generate（text-to-image / image-to-image）与 save_result_to_files（按 URL 下载图片并写 JSON），供评测脚本调用。输出路径：`output_dir/<model_subdir>/`，其中模型名中的 `/` 会变成子目录（如 `fal-ai/gpt-image-1.5/edit` → `tmp/fal-ai/gpt-image-1.5/edit/`），jpeg 与 json 均落在该目录下。
- **eval_prod_failed_prompts.py**：对 `tmp/scene_prompt_*.txt` 逐条读 prompt，调用 fal 生成并落盘；默认 text-to-image。传入 `--image-url` 时改为 image-to-image；传入 `--image-path` 时会先将该本地文件上传到 fal CDN，再用返回的 URL 做 image-to-image（无需自备公网 URL）。成功时图片与 JSON 写入 `output_dir/<model_subdir>/`；若某条 prompt 触发 fal 报错（如 422 content_policy_violation）：会打印异常、将完整错误信息写入同目录下 `{files_prefix}_fal_output_{timestamp}_error.json`，然后继续下一条。示例：`python -m experimental.eval_nana_banana.fal.eval_prod_failed_prompts --model fal-ai/gpt-image-1.5/edit --image-path tests/files/nurse_char_full_body.jpeg`。

根据初步评测，下面模型能处理超限提示词：

- fal-ai/bytedance/seedream/v4.5/edit <https://fal.ai/sandbox/share/I03ZcQbgF4II>
- fal-ai/gpt-image-1.5/edit <https://fal.ai/sandbox/share/I03ZcQbgF4II>

Models to test:

- fal-ai/gpt-image-1.5/edit
- fal-ai/bytedance/seedream/v4.5/edit
