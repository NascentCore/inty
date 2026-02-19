# 评测 Fal 上的图片模型

- **lib.py**：封装 fal 的 generate（text-to-image / image-to-image）与 save_result_to_files（按 URL 下载图片并写 JSON），供评测脚本调用。
- **eval_prod_failed_prompts.py**：对 `tmp/scene_prompt_*.txt` 逐条读 prompt，调用 fal 生成并落盘；默认 text-to-image。传入 `--image-url` 时改为 image-to-image；传入 `--image-path` 时会先将该本地文件上传到 fal CDN，再用返回的 URL 做 image-to-image（无需自备公网 URL）。示例：`python -m experimental.eval_nana_banana.fal.eval_prod_failed_prompts --model fal-ai/gpt-image-1.5/edit --image-path tests/files/nurse_char_full_body.jpeg`。

根据初步评测，下面模型能处理超限提示词：

- fal-ai/bytedance/seedream/v4.5/edit <https://fal.ai/sandbox/share/I03ZcQbgF4II>
- fal-ai/gpt-image-1.5/edit <https://fal.ai/sandbox/share/I03ZcQbgF4II>

Models to test:

- fal-ai/gpt-image-1.5/edit
- fal-ai/bytedance/seedream/v4.5/edit
